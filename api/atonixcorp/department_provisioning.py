from django.db import transaction
from rest_framework.exceptions import ValidationError

from .models import EntityDepartment
from .platform_foundation import log_platform_audit_event


DEPARTMENT_CATALOG = {
    'finance': {
        'name': 'Finance',
        'description': 'Financial planning, accounting operations, treasury, and reporting.',
        'cost_center': 'FIN-100',
    },
    'operations': {
        'name': 'Operations',
        'description': 'Operational delivery, process ownership, and service execution.',
        'cost_center': 'OPS-100',
    },
    'legal_compliance': {
        'name': 'Legal and Compliance',
        'description': 'Legal affairs, compliance controls, policy, and regulatory coordination.',
        'cost_center': 'LGL-100',
    },
    'human_resources': {
        'name': 'Human Resources',
        'description': 'People operations, workforce planning, and employment controls.',
        'cost_center': 'HR-100',
    },
    'technology': {
        'name': 'Technology',
        'description': 'Technology operations, security, systems, and data stewardship.',
        'cost_center': 'TEC-100',
    },
    'sales': {
        'name': 'Sales',
        'description': 'Commercial pipeline, customer acquisition, and revenue operations.',
        'cost_center': 'SAL-100',
    },
    'marketing': {
        'name': 'Marketing',
        'description': 'Brand, market strategy, demand generation, and communications.',
        'cost_center': 'MKT-100',
    },
    'risk_audit': {
        'name': 'Risk and Audit',
        'description': 'Enterprise risk, internal audit, control testing, and assurance.',
        'cost_center': 'RSK-100',
    },
    'equity_governance': {
        'name': 'Equity and Governance',
        'description': 'Shareholder records, equity administration, board governance, and reporting.',
        'cost_center': 'EQY-100',
    },
}


def validate_department_selections(values):
    if values in (None, ''):
        return []
    if not isinstance(values, list):
        raise ValidationError({'department_selections': 'Choose departments from the approved enterprise catalog.'})
    selections = list(dict.fromkeys(str(value or '').strip() for value in values if str(value or '').strip()))
    invalid = [value for value in selections if value not in DEPARTMENT_CATALOG]
    if invalid:
        raise ValidationError({'department_selections': f'Unsupported department selections: {", ".join(invalid)}.'})
    return selections


@transaction.atomic
def provision_selected_departments(entity, actor, selections):
    """Provision approved departments and mirror them to the entity workspace."""
    created_departments = []
    if not selections:
        return created_departments

    from workspaces.models import WorkspaceGroup

    workspace = getattr(entity, 'linked_workspace', None)
    for selection in selections:
        definition = DEPARTMENT_CATALOG[selection]
        department, created = EntityDepartment.objects.get_or_create(
            entity=entity,
            name=definition['name'],
            defaults={
                'code': f'{selection[:10].upper()}_{entity.id}',
                'description': definition['description'],
                'currency': entity.local_currency,
            },
        )
        if created:
            created_departments.append(department)
        if workspace:
            WorkspaceGroup.objects.get_or_create(
                workspace=workspace,
                name=department.name,
                defaults={
                    'description': department.description,
                    'owner': workspace.owner,
                    'cost_center': definition['cost_center'],
                },
            )

    if created_departments:
        log_platform_audit_event(
            domain='governance',
            event_type='department.provisioned',
            action='department_provisioned',
            actor=actor,
            organization=entity.organization,
            resource_type='Entity',
            resource_id=str(entity.id),
            resource_name=entity.name,
            summary=f'Provisioned {len(created_departments)} governed departments for {entity.name}',
            metadata={'department_codes': selections, 'department_names': [department.name for department in created_departments]},
        )
    return created_departments