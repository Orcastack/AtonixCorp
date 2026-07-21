from datetime import datetime, time

from django.utils import timezone

from .department_routing import apply_department_routing
from .models import PlatformAuditEvent, PlatformTask


TASK_REQUEST_LABELS = {
    'generate_statement': 'Generate Financial Statement',
    'run_tax_calculation': 'Run Tax Calculation',
    'import_bank_feed': 'Import Bank Feed',
    'process_payroll': 'Process Payroll',
    'custom': 'Custom Task',
}

TASK_REQUEST_STATUS_MAP = {
    'queued': 'open',
    'processing': 'in_progress',
    'completed': 'completed',
    'failed': 'blocked',
    'cancelled': 'cancelled',
}


def _build_search_text(domain, event_type, resource_type, resource_id, resource_name, summary, metadata, context=None, diff=None):
    parts = [domain, event_type, resource_type, resource_id, resource_name, summary]
    if isinstance(metadata, dict):
        parts.extend(str(value) for value in metadata.values() if value not in (None, ''))
    if isinstance(context, dict):
        parts.extend(str(value) for value in context.values() if value not in (None, ''))
    if isinstance(diff, dict):
        for value in diff.values():
            if isinstance(value, dict):
                parts.extend(str(nested) for nested in value.values() if nested not in (None, ''))
    return ' '.join(str(part) for part in parts if part)


def _resolve_actor_fields(actor=None, actor_type=None, actor_id=None):
    resolved_actor_type = actor_type or ('user' if actor else 'system')
    resolved_actor_id = actor_id or (str(actor.pk) if actor else '')
    return resolved_actor_type, resolved_actor_id


def log_platform_audit_event(*, domain, event_type=None, resource_type=None, resource_id=None, summary, actor=None, organization=None, entity=None, workspace_id=None, resource_name='', metadata=None, actor_type=None, actor_id=None, subject_type=None, subject_id=None, action=None, context=None, diff=None, correlation_id=''):
    metadata = metadata or {}
    context = context or {}
    diff = diff or {}
    event_type = event_type or action or 'event.recorded'
    resource_type = resource_type or subject_type or 'Unknown'
    resource_id = str(resource_id or subject_id or '')
    subject_type = subject_type or resource_type
    subject_id = str(subject_id or resource_id)
    action = action or event_type
    correlation_id = correlation_id or context.get('correlation_id', '') or metadata.get('correlation_id', '')
    resolved_actor_type, resolved_actor_id = _resolve_actor_fields(actor=actor, actor_type=actor_type, actor_id=actor_id)
    return PlatformAuditEvent.objects.create(
        organization=organization,
        entity=entity,
        workspace_id=workspace_id,
        actor=actor,
        actor_type=resolved_actor_type,
        actor_identifier='' if actor and resolved_actor_id == str(actor.pk) else resolved_actor_id,
        subject_type=subject_type,
        subject_id=subject_id,
        action=action,
        correlation_id=correlation_id,
        domain=domain,
        event_type=event_type,
        resource_type=resource_type,
        resource_id=resource_id,
        resource_name=resource_name,
        summary=summary,
        metadata=metadata,
        context=context,
        diff=diff,
        search_text=_build_search_text(domain, event_type, resource_type, resource_id, resource_name, summary, metadata, context, diff),
    )


def sync_task_request_to_platform_task(task_request):
    defaults = {
        'organization': task_request.organization,
        'entity': task_request.entity,
        'domain': 'finance',
        'task_type': task_request.task_type,
        'title': TASK_REQUEST_LABELS.get(task_request.task_type, task_request.task_type.replace('_', ' ').title()),
        'description': task_request.payload.get('description', '') if isinstance(task_request.payload, dict) else '',
        'status': TASK_REQUEST_STATUS_MAP.get(task_request.status, 'open'),
        'priority': task_request.priority,
        'assignee_type': 'user',
        'assignee_id': str(task_request.created_by_id or ''),
        'assigned_to': task_request.created_by,
        'created_by': task_request.created_by,
        'origin_type': 'task_request',
        'origin_id': str(task_request.id),
        'metadata': {
            'task_request_id': task_request.id,
            'payload': task_request.payload,
            'result': task_request.result,
            'error_message': task_request.error_message,
        },
        'started_at': task_request.started_at,
        'completed_at': task_request.completed_at,
    }
    defaults = apply_department_routing(defaults)
    platform_task, _ = PlatformTask.objects.update_or_create(
        domain='finance',
        source_object_type='TaskRequest',
        source_object_id=str(task_request.id),
        defaults=defaults,
    )
    return platform_task


def log_workspace_activity_as_platform_event(*, workspace_id, actor, action, metadata=None):
    metadata = metadata or {}
    resource_type = action.split('.', 1)[0].replace('_', ' ').title() or 'Workspace'
    summary = action.replace('.', ' ').replace('_', ' ')
    return log_platform_audit_event(
        domain='workspace',
        actor=actor,
        workspace_id=workspace_id,
        event_type=action,
        resource_type=resource_type,
        resource_id=str(workspace_id),
        subject_type='workspace',
        subject_id=str(workspace_id),
        action=action,
        resource_name=metadata.get('name', ''),
        summary=summary.title(),
        metadata=metadata,
        context=metadata.get('context', {}),
        diff=metadata.get('diff', {}),
    )


def create_platform_task(*, domain='platform', task_type, title, created_by, organization=None, entity=None, workspace_id=None, assigned_to=None, description='', priority='normal', due_at=None, metadata=None, source_object_type='', source_object_id=''):
    values = apply_department_routing({
        'organization': organization,
        'entity': entity,
        'workspace_id': workspace_id,
        'domain': domain,
        'task_type': task_type,
        'title': title,
        'description': description,
        'priority': priority,
        'due_at': due_at,
        'assignee_type': 'user' if assigned_to else 'user',
        'assignee_id': str(getattr(assigned_to, 'id', '') or ''),
        'assigned_to': assigned_to,
        'created_by': created_by,
        'origin_type': source_object_type,
        'origin_id': str(source_object_id or ''),
        'metadata': metadata or {},
        'source_object_type': source_object_type,
        'source_object_id': str(source_object_id or ''),
    })
    return PlatformTask.objects.create(**values)


def cancel_platform_tasks_for_origin(*, origin_type, origin_id):
    PlatformTask.objects.filter(origin_type=origin_type, origin_id=str(origin_id)).exclude(status__in=['completed', 'cancelled']).update(status='cancelled')


def _as_due_datetime(date_value):
    if not date_value:
        return None
    if isinstance(date_value, datetime):
        return date_value
    return timezone.make_aware(datetime.combine(date_value, time(hour=9)))


def sync_compliance_deadline_to_platform_task(deadline):
    status_map = {
        'completed': 'completed',
        'overdue': 'blocked',
        'due_soon': 'open',
        'upcoming': 'open',
    }
    priority_map = {
        'overdue': 'urgent',
        'due_soon': 'high',
        'upcoming': 'normal',
        'completed': 'normal',
    }
    defaults = {
        'organization': deadline.organization,
        'entity': deadline.entity,
        'domain': 'compliance',
        'task_type': f'compliance_{deadline.deadline_type}',
        'title': deadline.title,
        'description': deadline.description or '',
        'status': status_map.get(deadline.status, 'open'),
        'priority': priority_map.get(deadline.status, 'normal'),
        'assignee_type': 'user' if deadline.responsible_user_id else 'user',
        'assignee_id': str(deadline.responsible_user_id or ''),
        'assigned_to': deadline.responsible_user,
        'created_by': deadline.responsible_user,
        'due_at': _as_due_datetime(deadline.deadline_date),
        'completed_at': _as_due_datetime(deadline.completed_at) if deadline.completed_at else None,
        'origin_type': 'compliance_deadline',
        'origin_id': str(deadline.id),
        'metadata': {
            'deadline_type': deadline.deadline_type,
            'deadline_date': deadline.deadline_date.isoformat() if deadline.deadline_date else None,
            'status': deadline.status,
        },
    }
    defaults = apply_department_routing(defaults)
    task, _ = PlatformTask.objects.update_or_create(
        domain='compliance',
        source_object_type='ComplianceDeadline',
        source_object_id=str(deadline.id),
        defaults=defaults,
    )
    return task


def sync_accounting_approval_to_platform_task(record):
    status_map = {
        'draft': 'open',
        'pending_review': 'open',
        'pending_approval': 'in_progress',
        'approved': 'completed',
        'rejected': 'blocked',
    }
    defaults = {
        'organization': record.entity.organization,
        'entity': record.entity,
        'domain': 'approval',
        'task_type': f'approval_{record.object_type}',
        'title': record.title,
        'description': f'{record.get_object_type_display()} approval workflow',
        'status': status_map.get(record.status, 'open'),
        'priority': 'high',
        'assignee_type': 'role',
        'assignee_id': '',
        'assigned_to': None,
        'created_by': record.requested_by,
        'due_at': None,
        'completed_at': record.approved_at,
        'origin_type': record.object_type,
        'origin_id': str(record.object_id),
        'metadata': {
            'object_type': record.object_type,
            'object_id': record.object_id,
            'approval_status': record.status,
        },
    }
    defaults = apply_department_routing(defaults)
    task, _ = PlatformTask.objects.update_or_create(
        domain='approval',
        source_object_type='AccountingApprovalRecord',
        source_object_id=str(record.id),
        defaults=defaults,
    )
    return task


def sync_journal_entry_approval_task(entry):
    status_map = {
        'draft': 'open',
        'pending_review': 'open',
        'pending_approval': 'in_progress',
        'posted': 'completed',
        'rejected': 'blocked',
        'reversed': 'cancelled',
    }
    defaults = {
        'organization': entry.entity.organization,
        'entity': entry.entity,
        'domain': 'approval',
        'task_type': 'approval_journal_entry',
        'title': entry.reference_number,
        'description': entry.description or 'Journal entry approval workflow',
        'status': status_map.get(entry.status, 'open'),
        'priority': 'high',
        'assignee_type': 'role',
        'assignee_id': '',
        'assigned_to': None,
        'created_by': entry.created_by,
        'due_at': None,
        'completed_at': entry.approved_at,
        'origin_type': 'journal_entry',
        'origin_id': str(entry.id),
        'metadata': {
            'journal_entry_id': entry.id,
            'journal_status': entry.status,
            'amount_total': str(entry.amount_total or '0'),
        },
    }
    defaults = apply_department_routing(defaults)
    task, _ = PlatformTask.objects.update_or_create(
        domain='approval',
        source_object_type='JournalEntry',
        source_object_id=str(entry.id),
        defaults=defaults,
    )
    return task


def sync_document_request_to_platform_task(document_request):
    status_map = {
        'pending': 'open',
        'submitted': 'in_progress',
        'approved': 'completed',
        'rejected': 'blocked',
        'expired': 'cancelled',
    }
    defaults = {
        'organization': document_request.organization,
        'entity': None,
        'domain': 'document',
        'task_type': 'document_request',
        'title': f'{document_request.document_type} request',
        'description': document_request.description or '',
        'status': status_map.get(document_request.status, 'open'),
        'priority': 'normal',
        'assignee_type': 'user',
        'assignee_id': str(document_request.requested_by_id or ''),
        'assigned_to': None,
        'created_by': document_request.requested_by,
        'due_at': _as_due_datetime(document_request.due_date),
        'completed_at': timezone.now() if document_request.status == 'approved' else None,
        'origin_type': 'document_request',
        'origin_id': str(document_request.id),
        'metadata': {
            'client_id': document_request.client_id,
            'document_type': document_request.document_type,
            'status': document_request.status,
        },
    }
    defaults = apply_department_routing(defaults)
    task, _ = PlatformTask.objects.update_or_create(
        domain='document',
        source_object_type='DocumentRequest',
        source_object_id=str(document_request.id),
        defaults=defaults,
    )
    return task


def sync_equity_scenario_approval_task(approval):
    status_map = {
        'pending': 'open',
        'approved': 'completed',
        'rejected': 'blocked',
        'committed': 'completed',
    }
    defaults = {
        'organization': approval.workspace.organization,
        'entity': approval.workspace,
        'workspace_id': None,
        'domain': 'equity',
        'task_type': 'equity_transaction_approval',
        'title': approval.title,
        'description': approval.reporting_period or 'Equity scenario approval workflow',
        'status': status_map.get(approval.status, 'open'),
        'priority': 'high',
        'assignee_type': 'role',
        'assignee_id': 'board,legal',
        'assigned_to': None,
        'created_by': approval.requested_by,
        'due_at': approval.board_due_at or approval.legal_due_at,
        'completed_at': approval.board_decided_at or approval.legal_decided_at if approval.status == 'approved' else None,
        'origin_type': 'equity_scenario_approval',
        'origin_id': str(approval.id),
        'metadata': {
            'board_status': approval.board_status,
            'legal_status': approval.legal_status,
            'reporting_period': approval.reporting_period,
        },
    }
    defaults = apply_department_routing(defaults)
    task, _ = PlatformTask.objects.update_or_create(
        domain='equity',
        source_object_type='EquityScenarioApproval',
        source_object_id=str(approval.id),
        defaults=defaults,
    )
    return task