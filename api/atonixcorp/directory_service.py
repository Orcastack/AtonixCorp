"""LDAP-compatible organization directory synchronized from scoped RBAC records."""
from __future__ import annotations

from django.db import transaction
from django.utils.text import slugify

from .models import EntityDepartment, OrganizationDirectoryEntry, Permission, Role, TeamMember, UserProfile

DEFAULT_OFFICES = (
    ('finance', 'Finance'),
    ('technology', 'Technology'),
    ('security', 'Security'),
    ('governance', 'Governance'),
)

GOVERNANCE_ROLE_DEFAULTS = {
    'FOUNDER': ('Founder', ['manage_org_settings', 'manage_billing', 'manage_team', 'assign_roles']),
    'CEO': ('Chief Executive Officer', ['view_org_overview', 'view_entities', 'create_entity', 'edit_entity', 'view_reports', 'manage_team']),
    'CTO': ('Chief Technology Officer', ['view_org_overview', 'view_entities', 'edit_entity', 'view_reports']),
    'CSO': ('Chief Security Officer', ['view_org_overview', 'view_tax_compliance', 'view_risk_exposure', 'edit_risk_exposure', 'view_reports']),
    'BOARD': ('Board Member', ['view_org_overview', 'view_reports', 'view_risk_exposure']),
    'DEPARTMENT_HEAD': ('Department Head', ['view_entities', 'edit_entity', 'view_reports']),
    'UNIT_MEMBER': ('Unit Member', ['view_org_overview', 'view_entities']),
}


def _organization_dn(organization):
    organization_identity = organization.registration_number or slugify(organization.slug or organization.name)
    return f'o={slugify(organization_identity)},dc=atonixcorp'


def _ldap_uid(user):
    profile, _ = UserProfile.objects.get_or_create(user=user)
    return profile.secure_user_id


def _upsert_entry(organization, *, source_type, source_id, defaults):
    entry, _ = OrganizationDirectoryEntry.objects.update_or_create(
        organization=organization,
        source_type=source_type,
        source_id=str(source_id),
        defaults=defaults,
    )
    return entry


def ensure_governance_roles():
    for code, (name, permission_codes) in GOVERNANCE_ROLE_DEFAULTS.items():
        role, _ = Role.objects.get_or_create(code=code, defaults={'name': name, 'description': f'{name} governance role'})
        role.permissions.set(Permission.objects.filter(code__in=permission_codes))


@transaction.atomic
def sync_organization_directory(organization):
    """Refresh the directory projection; RBAC records remain the authorization source of truth."""
    ensure_governance_roles()
    department_ids = list(
        EntityDepartment.objects.filter(entity__organization=organization).values_list('id', flat=True)
    )
    member_ids = list(TeamMember.objects.filter(organization=organization).values_list('id', flat=True))
    from workspaces.models import Workspace, WorkspaceGroup

    workspace_ids = list(
        Workspace.objects.filter(linked_entity__organization=organization).values_list('id', flat=True)
    )
    workspace_group_ids = list(
        WorkspaceGroup.objects.filter(workspace__linked_entity__organization=organization).values_list('id', flat=True)
    )
    OrganizationDirectoryEntry.objects.filter(
        organization=organization,
        source_type='entity_department',
    ).exclude(source_id__in=[str(department_id) for department_id in department_ids]).delete()
    OrganizationDirectoryEntry.objects.filter(
        organization=organization,
        source_type='team_member',
    ).exclude(source_id__in=[str(member_id) for member_id in member_ids]).delete()
    OrganizationDirectoryEntry.objects.filter(
        organization=organization,
        source_type='workspace',
    ).exclude(source_id__in=[str(workspace_id) for workspace_id in workspace_ids]).delete()
    OrganizationDirectoryEntry.objects.filter(
        organization=organization,
        source_type='workspace_group',
    ).exclude(source_id__in=[str(group_id) for group_id in workspace_group_ids]).delete()
    root_dn = _organization_dn(organization)
    root = _upsert_entry(
        organization,
        source_type='organization',
        source_id=organization.id,
        defaults={
            'node_type': 'organization',
            'dn': root_dn,
            'cn': organization.name,
            'attributes': {
                'company_id': organization.id,
                'registration_number': organization.registration_number,
                'subscription_tier': (organization.settings or {}).get('subscription_tier', 'enterprise'),
            },
        },
    )

    offices = {}
    for office_key, office_name in DEFAULT_OFFICES:
        offices[office_key] = _upsert_entry(
            organization,
            source_type='default_office',
            source_id=office_key,
            defaults={
                'parent': root,
                'node_type': 'office',
                'dn': f'ou={office_key},{root_dn}',
                'cn': office_name,
                'attributes': {'office_key': office_key},
            },
        )

    owner_role = Role.objects.filter(code='ORG_OWNER').first()
    founder_permissions = list(owner_role.permissions.values_list('code', flat=True)) if owner_role else []
    _upsert_entry(
        organization,
        source_type='founder',
        source_id=organization.owner_id,
        defaults={
            'parent': root,
            'user': organization.owner,
            'node_type': 'user',
            'uid': _ldap_uid(organization.owner),
            'dn': f'uid={_ldap_uid(organization.owner)},ou=people,{root_dn}',
            'cn': organization.owner.get_full_name() or organization.owner.username,
            'role_code': 'FOUNDER',
            'permissions': founder_permissions,
            'attributes': {
                'email': organization.owner.email,
                'company_id': organization.id,
                'company_registration_number': organization.registration_number,
                'is_founder': True,
            },
            'is_active': True,
        },
    )

    for department in EntityDepartment.objects.filter(entity__organization=organization).select_related('entity'):
        office_key = 'finance' if 'finance' in department.name.lower() else 'governance'
        parent = offices[office_key]
        _upsert_entry(
            organization,
            source_type='entity_department',
            source_id=department.id,
            defaults={
                'parent': parent,
                'entity': department.entity,
                'node_type': 'department',
                'dn': f'ou={slugify(department.code)},{parent.dn}',
                'cn': department.name,
                'attributes': {'department_code': department.code, 'entity_id': department.entity_id},
                'is_active': department.is_active,
            },
        )

    workspace_entries = {}
    for workspace in Workspace.objects.filter(linked_entity__organization=organization).select_related('linked_entity'):
        workspace_key = f'{slugify(workspace.name)}-{str(workspace.id)[:8]}'
        workspace_entries[workspace.id] = _upsert_entry(
            organization,
            source_type='workspace',
            source_id=workspace.id,
            defaults={
                'parent': root,
                'entity': workspace.linked_entity,
                'node_type': 'office',
                'dn': f'ou={workspace_key},{root_dn}',
                'cn': workspace.name,
                'attributes': {'workspace_id': str(workspace.id), 'entity_id': workspace.linked_entity_id, 'tier': workspace.tier},
                'is_active': workspace.status == 'active',
            },
        )
    for group in WorkspaceGroup.objects.filter(workspace__linked_entity__organization=organization).select_related('workspace', 'workspace__linked_entity'):
        parent = workspace_entries.get(group.workspace_id)
        if parent is None:
            continue
        group_key = f'{slugify(group.name)}-{str(group.id)[:8]}'
        _upsert_entry(
            organization,
            source_type='workspace_group',
            source_id=group.id,
            defaults={
                'parent': parent,
                'entity': group.workspace.linked_entity,
                'node_type': 'unit',
                'dn': f'ou={group_key},{parent.dn}',
                'cn': group.name,
                'attributes': {
                    'workspace_id': str(group.workspace_id),
                    'cost_center': group.cost_center,
                    'owner_id': group.owner_id,
                },
                'is_active': parent.is_active,
            },
        )

    for member in TeamMember.objects.filter(organization=organization).select_related('user', 'role').prefetch_related('role__permissions'):
        if member.user_id == organization.owner_id:
            continue
        permissions = list(member.role.permissions.values_list('code', flat=True))
        _upsert_entry(
            organization,
            source_type='team_member',
            source_id=member.id,
            defaults={
                'parent': root,
                'user': member.user,
                'node_type': 'user',
                'uid': _ldap_uid(member.user),
                'dn': f'uid={_ldap_uid(member.user)},ou=people,{root_dn}',
                'cn': member.user.get_full_name() or member.user.username,
                'role_code': member.role.code,
                'permissions': permissions,
                'attributes': {
                    'email': member.user.email,
                    'company_id': organization.id,
                    'company_registration_number': organization.registration_number,
                    'scoped_entity_ids': list(member.scoped_entities.values_list('id', flat=True)),
                },
                'is_active': member.is_active,
            },
        )

    return root