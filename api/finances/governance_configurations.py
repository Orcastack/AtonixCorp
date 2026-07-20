"""Versioned YAML export, recovery, and workflow configuration for organizations."""
from __future__ import annotations

import hashlib
from datetime import date, datetime

import yaml
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .company_identity import normalize_registration_number
from .crypto_foundation import sign_governance_document, verify_governance_document
from .models import (
    AutomationWorkflow,
    Entity,
    EntityDepartment,
    EntityRole,
    GovernanceConfiguration,
    GovernancePolicy,
    Permission,
    Role,
    TeamMember,
)

SCHEMA_VERSION = 'v1'


def _primitive(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def _entity_payload(entity):
    return {
        'id': entity.id,
        'name': entity.name,
        'country': entity.country,
        'entity_type': entity.entity_type,
        'status': entity.status,
        'registration_number': entity.registration_number,
        'local_currency': entity.local_currency,
        'main_bank': entity.main_bank,
        'tax_authority_url': entity.tax_authority_url,
        'fiscal_year_end': _primitive(entity.fiscal_year_end),
        'next_filing_date': _primitive(entity.next_filing_date),
        'workspace_mode': entity.workspace_mode,
        'industry': entity.industry,
        'workspace_type': entity.workspace_type,
        'workspace_template_key': entity.workspace_template_key,
        'hierarchy_metadata': entity.hierarchy_metadata,
        'dashboard_config': entity.dashboard_config,
        'rbac_config': entity.rbac_config,
        'enabled_modules': entity.enabled_modules,
        'parent_entity_id': entity.parent_entity_id,
        'departments': [
            {
                'name': department.name,
                'code': department.code,
                'description': department.description,
                'budget': str(department.budget) if department.budget is not None else None,
                'currency': department.currency,
                'is_active': department.is_active,
            }
            for department in entity.departments.all()
        ],
        'roles': [
            {
                'name': role.name,
                'code': role.code,
                'description': role.description,
                'department_code': role.department.code if role.department else None,
                'salary_range_min': str(role.salary_range_min) if role.salary_range_min is not None else None,
                'salary_range_max': str(role.salary_range_max) if role.salary_range_max is not None else None,
                'currency': role.currency,
                'is_active': role.is_active,
                'permissions': list(role.permissions.values_list('code', flat=True)),
            }
            for role in entity.roles.prefetch_related('permissions', 'department').all()
        ],
    }


def build_governance_document(organization):
    from workspaces.models import Workspace

    entities = list(
        organization.entities.select_related('parent_entity')
        .prefetch_related('departments', 'roles__permissions', 'roles__department')
        .order_by('id')
    )
    return {
        'schema_version': SCHEMA_VERSION,
        'document_type': 'atonixcorp_governance_configuration',
        'generated_at': timezone.now().isoformat(),
        'organization': {
            'id': organization.id,
            'name': organization.name,
            'registration_number': organization.registration_number,
            'slug': organization.slug,
            'description': organization.description,
            'industry': organization.industry,
            'subscription_tier': (organization.settings or {}).get('subscription_tier', 'enterprise'),
            'primary_country': organization.primary_country,
            'primary_currency': organization.primary_currency,
            'settings': organization.settings,
        },
        'entities': [_entity_payload(entity) for entity in entities],
        'offices': [
            {
                'entity_id': workspace.linked_entity_id,
                'name': workspace.name,
                'description': workspace.description,
                'tier': workspace.tier,
                'status': workspace.status,
                'departments': [
                    {
                        'name': group.name,
                        'description': group.description,
                        'cost_center': group.cost_center,
                    }
                    for group in workspace.groups.all()
                ],
            }
            for workspace in Workspace.objects.filter(linked_entity__organization=organization)
            .select_related('linked_entity')
            .prefetch_related('groups')
            .order_by('name')
        ],
        'governance_policies': [
            {
                'policy_code': policy.policy_code,
                'title': policy.title,
                'edition': policy.edition,
                'status': policy.status,
                'summary': policy.summary,
                'source_document': policy.source_document,
                'effective_date': _primitive(policy.effective_date),
                'next_review_date': _primitive(policy.next_review_date),
            }
            for policy in organization.governance_policies.order_by('policy_code', 'edition')
        ],
        'workflows': [
            {
                'name': workflow.name,
                'description': workflow.description,
                'trigger_type': workflow.trigger_type,
                'trigger_config': workflow.trigger_config,
                'actions': workflow.actions,
                'is_active': workflow.is_active,
                'entity_id': workflow.entity_id,
            }
            for workflow in organization.automation_workflows.order_by('id')
        ],
        'ldap_directory': [
            {
                'uid': entry.uid,
                'dn': entry.dn,
                'cn': entry.cn,
                'node_type': entry.node_type,
                'role_code': entry.role_code,
                'permissions': entry.permissions,
                'source_type': entry.source_type,
                'attributes': entry.attributes,
                'is_active': entry.is_active,
            }
            for entry in organization.directory_entries.order_by('dn')
        ],
    }


def render_governance_yaml(organization):
    document = build_governance_document(organization)
    document['integrity'] = sign_governance_document(document)
    return yaml.safe_dump(
        document,
        allow_unicode=False,
        default_flow_style=False,
        sort_keys=False,
    )


def refresh_governance_configuration(organization):
    if not organization or not organization.pk:
        return None
    rendered = render_governance_yaml(organization)
    checksum = hashlib.sha256(rendered.encode('utf-8')).hexdigest()
    configuration, _ = GovernanceConfiguration.objects.get_or_create(organization=organization)
    if configuration.checksum == checksum and configuration.configuration_file:
        return configuration

    configuration.schema_version = SCHEMA_VERSION
    configuration.revision += 1
    configuration.checksum = checksum
    filename = f'org-{organization.pk}-config.yml'
    configuration.configuration_file.save(filename, ContentFile(rendered.encode('utf-8')), save=False)
    configuration.save()
    return configuration


def _required_mapping(value, key):
    if not isinstance(value, dict):
        raise ValidationError({key: 'Must be an object.'})
    return value


def _parse_date(value, key):
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError) as error:
        raise ValidationError({key: 'Must be an ISO-8601 date.'}) from error


@transaction.atomic
def restore_governance_document(organization, document):
    document = _required_mapping(document, 'configuration')
    verify_governance_document(document)
    if document.get('document_type') != 'atonixcorp_governance_configuration':
        raise ValidationError({'configuration': 'Unsupported governance configuration document.'})
    if document.get('schema_version') != SCHEMA_VERSION:
        raise ValidationError({'schema_version': f'Only {SCHEMA_VERSION} configurations are supported.'})

    organization_data = _required_mapping(document.get('organization'), 'organization')
    if organization.registration_number:
        document_registration_number = organization_data.get('registration_number')
        if not document_registration_number:
            raise ValidationError({'organization.registration_number': 'Company registration number is required for recovery.'})
        try:
            normalized_document_registration_number = normalize_registration_number(document_registration_number)
        except Exception as error:
            raise ValidationError({'organization.registration_number': str(error)})
        if normalized_document_registration_number != organization.registration_number:
            raise ValidationError({'organization.registration_number': 'Configuration belongs to a different company.'})
    organization.name = organization_data.get('name', organization.name)
    organization.description = organization_data.get('description', organization.description)
    organization.industry = organization_data.get('industry', organization.industry)
    organization.primary_country = organization_data.get('primary_country', organization.primary_country)
    organization.primary_currency = organization_data.get('primary_currency', organization.primary_currency)
    organization.settings = organization_data.get('settings', organization.settings) or {}
    organization.save()

    entity_id_map = {}
    entity_rows = document.get('entities', [])
    if not isinstance(entity_rows, list):
        raise ValidationError({'entities': 'Must be a list.'})
    for row in entity_rows:
        row = _required_mapping(row, 'entities')
        entity, _ = Entity.objects.update_or_create(
            organization=organization,
            name=row.get('name', ''),
            country=row.get('country', ''),
            defaults={
                'entity_type': row.get('entity_type', 'other'),
                'status': row.get('status', 'active'),
                'registration_number': row.get('registration_number', ''),
                'local_currency': row.get('local_currency', organization.primary_currency),
                'main_bank': row.get('main_bank', ''),
                'tax_authority_url': row.get('tax_authority_url', ''),
                'fiscal_year_end': _parse_date(row.get('fiscal_year_end'), 'fiscal_year_end'),
                'next_filing_date': _parse_date(row.get('next_filing_date'), 'next_filing_date'),
                'workspace_mode': row.get('workspace_mode', 'accounting'),
                'industry': row.get('industry', ''),
                'workspace_type': row.get('workspace_type', ''),
                'workspace_template_key': row.get('workspace_template_key', ''),
                'hierarchy_metadata': row.get('hierarchy_metadata', {}) or {},
                'dashboard_config': row.get('dashboard_config', {}) or {},
                'rbac_config': row.get('rbac_config', {}) or {},
                'enabled_modules': row.get('enabled_modules', []) or [],
            },
        )
        entity_id_map[row.get('id')] = entity

        departments = {}
        for department_data in row.get('departments', []):
            department_data = _required_mapping(department_data, 'departments')
            department, _ = EntityDepartment.objects.update_or_create(
                entity=entity,
                code=department_data.get('code', ''),
                defaults={
                    'name': department_data.get('name', ''),
                    'description': department_data.get('description', ''),
                    'budget': department_data.get('budget'),
                    'currency': department_data.get('currency', entity.local_currency),
                    'is_active': department_data.get('is_active', True),
                },
            )
            departments[department.code] = department

        for role_data in row.get('roles', []):
            role_data = _required_mapping(role_data, 'roles')
            role, _ = EntityRole.objects.update_or_create(
                entity=entity,
                code=role_data.get('code', ''),
                defaults={
                    'name': role_data.get('name', ''),
                    'description': role_data.get('description', ''),
                    'department': departments.get(role_data.get('department_code')),
                    'salary_range_min': role_data.get('salary_range_min'),
                    'salary_range_max': role_data.get('salary_range_max'),
                    'currency': role_data.get('currency', entity.local_currency),
                    'is_active': role_data.get('is_active', True),
                },
            )
            role.permissions.set(Permission.objects.filter(code__in=role_data.get('permissions', [])))

    for row in entity_rows:
        entity = entity_id_map.get(row.get('id'))
        parent = entity_id_map.get(row.get('parent_entity_id'))
        if entity and parent and entity.parent_entity_id != parent.id:
            entity.parent_entity = parent
            entity.save(update_fields=['parent_entity', 'updated_at'])

    from workspaces.models import Workspace, WorkspaceGroup
    for office_data in document.get('offices', []):
        office_data = _required_mapping(office_data, 'offices')
        entity = entity_id_map.get(office_data.get('entity_id'))
        if entity is None:
            continue
        workspace, _ = Workspace.objects.get_or_create(
            linked_entity=entity,
            defaults={
                'owner': organization.owner,
                'name': office_data.get('name', entity.name),
                'description': office_data.get('description', ''),
                'tier': office_data.get('tier', 'free'),
                'status': office_data.get('status', 'active'),
            },
        )
        for department_data in office_data.get('departments', []):
            department_data = _required_mapping(department_data, 'offices.departments')
            WorkspaceGroup.objects.update_or_create(
                workspace=workspace,
                name=department_data.get('name', ''),
                defaults={
                    'description': department_data.get('description', ''),
                    'cost_center': department_data.get('cost_center', ''),
                    'owner': organization.owner,
                },
            )

    for policy_data in document.get('governance_policies', []):
        policy_data = _required_mapping(policy_data, 'governance_policies')
        GovernancePolicy.objects.update_or_create(
            organization=organization,
            policy_code=policy_data.get('policy_code', ''),
            edition=policy_data.get('edition', '1.0'),
            defaults={
                'title': policy_data.get('title', ''),
                'status': policy_data.get('status', 'draft'),
                'summary': policy_data.get('summary', ''),
                'source_document': policy_data.get('source_document', ''),
                'effective_date': _parse_date(policy_data.get('effective_date'), 'effective_date'),
                'next_review_date': _parse_date(policy_data.get('next_review_date'), 'next_review_date'),
            },
        )

    for workflow_data in document.get('workflows', []):
        workflow_data = _required_mapping(workflow_data, 'workflows')
        entity = entity_id_map.get(workflow_data.get('entity_id'))
        AutomationWorkflow.objects.update_or_create(
            organization=organization,
            name=workflow_data.get('name', ''),
            defaults={
                'entity': entity,
                'description': workflow_data.get('description', ''),
                'trigger_type': workflow_data.get('trigger_type', 'manual'),
                'trigger_config': workflow_data.get('trigger_config', {}) or {},
                'actions': workflow_data.get('actions', []) or [],
                'is_active': workflow_data.get('is_active', True),
                'created_by': organization.owner,
            },
        )

    from django.contrib.auth.models import User
    from django.utils.text import slugify
    from .directory_service import ensure_governance_roles, sync_organization_directory

    ensure_governance_roles()
    directory_entries = document.get('ldap_directory', [])
    if not isinstance(directory_entries, list):
        raise ValidationError({'ldap_directory': 'Must be a list.'})
    for entry_data in directory_entries:
        entry_data = _required_mapping(entry_data, 'ldap_directory')
        if entry_data.get('node_type') != 'user' or entry_data.get('role_code') in {'', 'FOUNDER', 'ORG_OWNER'}:
            continue
        attributes = entry_data.get('attributes') or {}
        email = str(attributes.get('email') or '').strip().lower()
        if not email:
            continue
        user = User.objects.filter(email=email).first()
        if user is None:
            base_username = slugify(email.split('@')[0]) or 'recovered-user'
            username = base_username
            suffix = 1
            while User.objects.filter(username=username).exists():
                suffix += 1
                username = f'{base_username}-{suffix}'
            user = User.objects.create_user(username=username, email=email)
            user.set_unusable_password()
            user.is_active = False
            user.save(update_fields=['password', 'is_active'])
        role = Role.objects.filter(code=entry_data['role_code']).first()
        if role is None:
            raise ValidationError({'ldap_directory': f"Unknown role code: {entry_data['role_code']}."})
        member, _ = TeamMember.objects.update_or_create(
            organization=organization,
            user=user,
            defaults={'role': role, 'is_active': bool(entry_data.get('is_active', True)), 'accepted_at': None},
        )
        scoped_entities = [entity_id_map.get(entity_id) for entity_id in attributes.get('scoped_entity_ids', [])]
        member.scoped_entities.set([entity for entity in scoped_entities if entity])

    sync_organization_directory(organization)

    return refresh_governance_configuration(organization)