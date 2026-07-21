from decimal import Decimal

from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone

from .accounting_controls import ensure_period_is_open, get_staff_for_user, user_has_role
from .accounting_notification_delivery import build_approval_action_url, dispatch_approval_request_notifications
from .models import (
    AccountingApprovalChangeLog,
    AccountingApprovalDelegation,
    AccountingApprovalMatrix,
    AccountingApprovalRecord,
    AccountingApprovalStep,
    Bill,
    BillPayment,
    Notification,
    Payment,
    PayrollRun,
    PurchaseOrder,
)
from .platform_foundation import log_platform_audit_event, sync_accounting_approval_to_platform_task
from .payroll_engine import estimate_payroll_run_amount


ACCOUNTING_OBJECT_CONFIG = {
    'purchase_order': {
        'model': PurchaseOrder,
        'date_field': 'po_date',
        'amount_field': 'total_amount',
        'title_field': 'po_number',
        'status_field': 'status',
        'final_status': 'posted',
    },
    'bill': {
        'model': Bill,
        'date_field': 'bill_date',
        'amount_field': 'total_amount',
        'title_field': 'bill_number',
        'status_field': 'status',
        'final_status': 'posted',
    },
    'bill_payment': {
        'model': BillPayment,
        'date_field': 'payment_date',
        'amount_field': 'amount',
        'title_field': 'reference_number',
        'status_field': None,
        'final_status': None,
    },
    'payment': {
        'model': Payment,
        'date_field': 'payment_date',
        'amount_field': 'amount',
        'title_field': 'reference_number',
        'status_field': None,
        'final_status': None,
    },
    'payroll_run': {
        'model': PayrollRun,
        'date_field': 'payment_date',
        'amount_field': None,
        'amount_resolver': estimate_payroll_run_amount,
        'title_field': 'name',
        'status_field': None,
        'final_status': None,
    },
}


def infer_accounting_object_type(instance):
    if isinstance(instance, PurchaseOrder):
        return 'purchase_order'
    if isinstance(instance, Bill):
        return 'bill'
    if isinstance(instance, BillPayment):
        return 'bill_payment'
    if isinstance(instance, Payment):
        return 'payment'
    if isinstance(instance, PayrollRun):
        return 'payroll_run'
    raise ValueError('Unsupported accounting object for approval workflow.')


def _resolve_amount(instance, config):
    resolver = config.get('amount_resolver')
    if resolver:
        return Decimal(str(resolver(instance) or 0))
    return Decimal(getattr(instance, config['amount_field'], 0) or 0)


def _resolve_title(instance, config, object_type):
    return getattr(instance, config['title_field'], '') or f'{object_type}-{instance.id}'


def get_accounting_object(object_type, object_id):
    config = ACCOUNTING_OBJECT_CONFIG.get(object_type)
    if not config:
        raise ValueError('Unsupported approval object type.')
    return config['model'].objects.get(id=object_id)


def snapshot_accounting_object(instance, object_type=None):
    object_type = object_type or infer_accounting_object_type(instance)
    config = ACCOUNTING_OBJECT_CONFIG[object_type]
    amount = _resolve_amount(instance, config)
    title_value = _resolve_title(instance, config, object_type)
    return {
        'id': instance.id,
        'object_type': object_type,
        'entity': instance.entity_id,
        'title': title_value,
        'amount': str(amount),
        'approval_status': getattr(instance, 'approval_status', 'draft'),
        'approved_by': getattr(instance, 'approved_by_id', None),
        'approved_at': instance.approved_at.isoformat() if getattr(instance, 'approved_at', None) else None,
        'approval_submitted_at': instance.approval_submitted_at.isoformat() if getattr(instance, 'approval_submitted_at', None) else None,
    }


def log_accounting_change(record, action, actor=None, stage='', details='', old_values=None, new_values=None):
    return AccountingApprovalChangeLog.objects.create(
        approval=record,
        entity=record.entity,
        actor=actor,
        action=action,
        stage=stage,
        details=details,
        old_values=old_values or {},
        new_values=new_values or {},
    )


def get_matching_accounting_matrix(instance, object_type=None):
    object_type = object_type or infer_accounting_object_type(instance)
    config = ACCOUNTING_OBJECT_CONFIG[object_type]
    amount = _resolve_amount(instance, config)
    applicable = []
    matrices = AccountingApprovalMatrix.objects.filter(
        entity=instance.entity,
        object_type=object_type,
        is_active=True,
    ).select_related('preparer_role', 'reviewer_role', 'approver_role')

    for matrix in matrices:
        if amount < (matrix.minimum_amount or Decimal('0')):
            continue
        if matrix.maximum_amount is not None and amount > matrix.maximum_amount:
            continue
        applicable.append(matrix)

    if not applicable:
        return None

    applicable.sort(
        key=lambda matrix: (
            matrix.minimum_amount or Decimal('0'),
            0 if matrix.maximum_amount is None else -(matrix.maximum_amount),
            matrix.updated_at.timestamp() if matrix.updated_at else 0,
            matrix.id or 0,
        ),
        reverse=True,
    )
    return applicable[0]


def _get_or_create_record(instance, object_type=None):
    object_type = object_type or infer_accounting_object_type(instance)
    config = ACCOUNTING_OBJECT_CONFIG[object_type]
    title_value = _resolve_title(instance, config, object_type)
    amount = _resolve_amount(instance, config)
    record, _ = AccountingApprovalRecord.objects.get_or_create(
        object_type=object_type,
        object_id=instance.id,
        defaults={
            'entity': instance.entity,
            'title': title_value,
            'amount': amount,
            'status': getattr(instance, 'approval_status', 'draft') or 'draft',
            'requested_by': getattr(instance, 'created_by', None),
        },
    )
    changed_fields = []
    if record.entity_id != instance.entity_id:
        record.entity = instance.entity
        changed_fields.append('entity')
    if record.title != title_value:
        record.title = title_value
        changed_fields.append('title')
    if record.amount != amount:
        record.amount = amount
        changed_fields.append('amount')
    requested_by = getattr(instance, 'created_by', None)
    if requested_by and record.requested_by_id != requested_by.id:
        record.requested_by = requested_by
        changed_fields.append('requested_by')
    if changed_fields:
        record.save(update_fields=changed_fields + ['updated_at'])
    return record


def _sync_instance_from_record(instance, record):
    update_fields = ['approval_status', 'approval_submitted_at', 'approved_by', 'approved_at']
    instance.approval_status = record.status
    instance.approval_submitted_at = record.submitted_at
    instance.approved_by = record.approved_by
    instance.approved_at = record.approved_at

    config = ACCOUNTING_OBJECT_CONFIG[infer_accounting_object_type(instance)]
    status_field = config['status_field']
    if status_field:
        if record.status == 'approved' and config['final_status']:
            setattr(instance, status_field, config['final_status'])
        elif getattr(instance, status_field) != 'cancelled':
            setattr(instance, status_field, 'draft')
        update_fields.append(status_field)
    if hasattr(instance, 'updated_at'):
        update_fields.append('updated_at')
    instance.save(update_fields=update_fields)


def _deliver_approval_notifications(record, step):
    if not step.assigned_role_id:
        return

    recipients = set(
        step.assigned_role.staff.filter(status='active').exclude(user_id__isnull=True).values_list('user_id', flat=True)
    )

    today = timezone.now().date()
    delegations = AccountingApprovalDelegation.objects.filter(
        entity=record.entity,
        stage=step.stage,
        is_active=True,
        delegate__status='active',
        start_date__lte=today,
        end_date__gte=today,
    )
    if record.object_type:
        delegations = delegations.filter(object_type__in=['', record.object_type])

    for delegation in delegations.select_related('delegate__user', 'delegator__role'):
        if delegation.delegator.role_id != step.assigned_role_id:
            continue
        if delegation.delegate.user_id:
            recipients.add(delegation.delegate.user_id)

    dispatch_approval_request_notifications(
        users=User.objects.filter(id__in=recipients),
        organization=record.entity.organization,
        entity=record.entity,
        title=f'{record.get_object_type_display()} approval required',
        message=f'{record.title} is awaiting {step.stage} approval.',
        related_content_type=record.object_type,
        related_object_id=record.object_id,
        action_url=build_approval_action_url(
            related_content_type=record.object_type,
            entity_id=record.entity_id,
            related_object_id=record.object_id,
        ),
    )


def _validate_accounting_matrix(instance, matrix):
    if matrix is None:
        raise ValueError('No active approval matrix matches this accounting object. Configure a matrix before submitting.')

    creator = getattr(instance, 'created_by', None)
    if matrix.preparer_role and not user_has_role(instance.entity, creator, matrix.preparer_role):
        raise ValueError('The preparer does not satisfy the configured preparer role.')
    if matrix.require_reviewer and not matrix.reviewer_role:
        raise ValueError('The approval matrix requires a reviewer role.')
    if matrix.require_approver and not matrix.approver_role:
        raise ValueError('The approval matrix requires an approver role.')


def _current_pending_step(record):
    return record.steps.filter(status='pending').order_by('step_order').first()


def _actor_ids(record):
    actor_ids = set()
    if record.requested_by_id:
        actor_ids.add(record.requested_by_id)
    actor_ids.update(record.steps.exclude(acted_by_id__isnull=True).values_list('acted_by_id', flat=True))
    return actor_ids


def _find_active_delegation(record, step, actor):
    staff_member = get_staff_for_user(record.entity, actor)
    if not staff_member:
        return None
    today = timezone.now().date()
    delegations = AccountingApprovalDelegation.objects.filter(
        entity=record.entity,
        delegate=staff_member,
        stage=step.stage,
        is_active=True,
        start_date__lte=today,
        end_date__gte=today,
        object_type__in=['', record.object_type],
    ).select_related('delegator__role')
    for delegation in delegations:
        if step.assigned_role_id and delegation.delegator.role_id != step.assigned_role_id:
            continue
        if record.amount < (delegation.minimum_amount or Decimal('0')):
            continue
        if delegation.maximum_amount is not None and record.amount > delegation.maximum_amount:
            continue
        return delegation
    return None


def _authorize_record_step(record, step, actor):
    if actor.id == record.requested_by_id and step.stage in ['reviewer', 'approver']:
        raise ValueError('Segregation of duties prevents the preparer from approving this item.')

    if actor.id in _actor_ids(record) and step.stage == 'approver':
        raise ValueError('Segregation of duties requires a different approver than earlier workflow actors.')

    if step.assigned_role and user_has_role(record.entity, actor, step.assigned_role):
        return None
    delegation = _find_active_delegation(record, step, actor)
    if delegation:
        return delegation
    raise ValueError('You are not authorized to act on the current approval step.')


def _apply_execution_effects(instance, object_type):
    if object_type == 'payment':
        invoice = instance.invoice
        invoice.paid_amount += instance.amount
        invoice.outstanding_amount = max(invoice.total_amount - invoice.paid_amount, Decimal('0'))
        if invoice.outstanding_amount == 0 and invoice.paid_amount > 0:
            invoice.status = 'paid'
        elif invoice.paid_amount > 0:
            invoice.status = 'partially_paid'
        invoice.save(update_fields=['paid_amount', 'outstanding_amount', 'status', 'updated_at'])
    elif object_type == 'bill_payment':
        bill = instance.bill
        bill.paid_amount += instance.amount
        bill.outstanding_amount = max(bill.total_amount - bill.paid_amount, Decimal('0'))
        if bill.outstanding_amount == 0 and bill.paid_amount > 0:
            bill.status = 'paid'
        elif bill.paid_amount > 0:
            bill.status = 'partially_paid'
        bill.save(update_fields=['paid_amount', 'outstanding_amount', 'status', 'updated_at'])


@transaction.atomic
def submit_accounting_object(instance, actor, object_type=None):
    object_type = object_type or infer_accounting_object_type(instance)
    if getattr(instance, 'approval_status', 'draft') not in ['draft', 'rejected']:
        raise ValueError('Only draft or rejected items can be submitted.')

    config = ACCOUNTING_OBJECT_CONFIG[object_type]
    ensure_period_is_open(instance.entity, getattr(instance, config['date_field']))
    matrix = get_matching_accounting_matrix(instance, object_type)
    _validate_accounting_matrix(instance, matrix)

    record = _get_or_create_record(instance, object_type)
    record.steps.all().delete()
    created_staff = get_staff_for_user(instance.entity, getattr(instance, 'created_by', None))
    AccountingApprovalStep.objects.create(
        approval=record,
        step_order=1,
        stage='preparer',
        assigned_role=matrix.preparer_role,
        assigned_staff=created_staff,
        status='approved',
        acted_by=getattr(instance, 'created_by', None),
        acted_at=timezone.now(),
        comments='Prepared and submitted.',
    )

    step_order = 2
    pending_status = 'pending_approval'
    next_step = None
    if matrix.require_reviewer:
        next_step = AccountingApprovalStep.objects.create(
            approval=record,
            step_order=step_order,
            stage='reviewer',
            assigned_role=matrix.reviewer_role,
            status='pending',
        )
        step_order += 1
        pending_status = 'pending_review'
    if matrix.require_approver:
        approver_step = AccountingApprovalStep.objects.create(
            approval=record,
            step_order=step_order,
            stage='approver',
            assigned_role=matrix.approver_role,
            status='pending',
        )
        if next_step is None:
            next_step = approver_step

    old_snapshot = snapshot_accounting_object(instance, object_type)
    record.status = pending_status
    record.submitted_at = timezone.now()
    record.requested_by = getattr(instance, 'created_by', None)
    record.approved_by = None
    record.approved_at = None
    record.save(update_fields=['status', 'submitted_at', 'requested_by', 'approved_by', 'approved_at', 'updated_at'])
    _sync_instance_from_record(instance, record)

    log_accounting_change(
        record,
        'matrix_applied',
        actor=actor,
        details=f'Applied matrix {matrix.name}.',
        new_values={
            'matrix': matrix.name,
            'reviewer_role': matrix.reviewer_role.name if matrix.reviewer_role else None,
            'approver_role': matrix.approver_role.name if matrix.approver_role else None,
        },
    )
    log_accounting_change(
        record,
        'submitted',
        actor=actor,
        details=f'{record.get_object_type_display()} submitted into the approval workflow.',
        old_values=old_snapshot,
        new_values=snapshot_accounting_object(instance, object_type),
    )
    sync_accounting_approval_to_platform_task(record)
    log_platform_audit_event(
        domain='finance',
        actor=actor,
        organization=record.entity.organization,
        entity=record.entity,
        event_type='accounting_approval.submitted',
        action='approval_requested',
        resource_type='AccountingApprovalRecord',
        resource_id=str(record.id),
        subject_type=record.object_type,
        subject_id=str(record.object_id),
        resource_name=record.title,
        summary=f'{record.get_object_type_display()} submitted for approval: {record.title}',
        diff={'before': old_snapshot, 'after': snapshot_accounting_object(instance, object_type)},
        context={'approval_status': record.status, 'stage': next_step.stage if next_step else ''},
        metadata={'approval_record_id': record.id},
    )
    if next_step:
        _deliver_approval_notifications(record, next_step)
    return record


@transaction.atomic
def approve_accounting_object(record, actor, comments=''):
    if record.status not in ['pending_review', 'pending_approval']:
        raise ValueError('This item is not awaiting approval.')
    instance = get_accounting_object(record.object_type, record.object_id)
    config = ACCOUNTING_OBJECT_CONFIG[record.object_type]
    ensure_period_is_open(instance.entity, getattr(instance, config['date_field']))

    step = _current_pending_step(record)
    if not step:
        raise ValueError('No pending approval step was found for this item.')
    delegation = _authorize_record_step(record, step, actor)
    previous = snapshot_accounting_object(instance, record.object_type)

    step.status = 'approved'
    step.acted_by = actor
    step.acted_at = timezone.now()
    step.comments = comments or step.comments
    step.delegated_from = delegation
    step.save(update_fields=['status', 'acted_by', 'acted_at', 'comments', 'delegated_from', 'updated_at'])

    next_step = _current_pending_step(record)
    if next_step and next_step.stage == 'approver':
        record.status = 'pending_approval'
        record.save(update_fields=['status', 'updated_at'])
        _deliver_approval_notifications(record, next_step)
    elif next_step:
        record.status = 'pending_review'
        record.save(update_fields=['status', 'updated_at'])
        _deliver_approval_notifications(record, next_step)
    else:
        record.status = 'approved'
        record.approved_by = actor
        record.approved_at = timezone.now()
        record.save(update_fields=['status', 'approved_by', 'approved_at', 'updated_at'])
        _sync_instance_from_record(instance, record)
        _apply_execution_effects(instance, record.object_type)
        log_accounting_change(
            record,
            'executed',
            actor=actor,
            details='Final approval posted business effects.',
            new_values=snapshot_accounting_object(instance, record.object_type),
        )
        sync_accounting_approval_to_platform_task(record)
        log_platform_audit_event(
            domain='finance',
            actor=actor,
            organization=record.entity.organization,
            entity=record.entity,
            event_type='accounting_approval.completed',
            action='approval_completed',
            resource_type='AccountingApprovalRecord',
            resource_id=str(record.id),
            subject_type=record.object_type,
            subject_id=str(record.object_id),
            resource_name=record.title,
            summary=f'{record.get_object_type_display()} approved: {record.title}',
            diff={'before': previous, 'after': snapshot_accounting_object(instance, record.object_type)},
            context={'approval_status': record.status},
            metadata={'approval_record_id': record.id},
        )
        return record

    _sync_instance_from_record(instance, record)
    log_accounting_change(
        record,
        'approved',
        actor=actor,
        stage=step.stage,
        details='Delegated authority exercised.' if delegation else 'Approval step completed.',
        old_values=previous,
        new_values=snapshot_accounting_object(instance, record.object_type),
    )
    sync_accounting_approval_to_platform_task(record)
    log_platform_audit_event(
        domain='finance',
        actor=actor,
        organization=record.entity.organization,
        entity=record.entity,
        event_type='accounting_approval.progressed',
        action='approval_progressed',
        resource_type='AccountingApprovalRecord',
        resource_id=str(record.id),
        subject_type=record.object_type,
        subject_id=str(record.object_id),
        resource_name=record.title,
        summary=f'{record.get_object_type_display()} approval advanced: {record.title}',
        diff={'before': previous, 'after': snapshot_accounting_object(instance, record.object_type)},
        context={'approval_status': record.status, 'stage': step.stage},
        metadata={'approval_record_id': record.id},
    )
    return record


@transaction.atomic
def reject_accounting_object(record, actor, comments=''):
    if record.status not in ['pending_review', 'pending_approval']:
        raise ValueError('This item is not awaiting approval.')
    instance = get_accounting_object(record.object_type, record.object_id)
    step = _current_pending_step(record)
    if not step:
        raise ValueError('No pending approval step was found for this item.')
    _authorize_record_step(record, step, actor)

    previous = snapshot_accounting_object(instance, record.object_type)
    step.status = 'rejected'
    step.acted_by = actor
    step.acted_at = timezone.now()
    step.comments = comments or step.comments
    step.save(update_fields=['status', 'acted_by', 'acted_at', 'comments', 'updated_at'])

    record.status = 'rejected'
    record.approved_by = None
    record.approved_at = None
    record.save(update_fields=['status', 'approved_by', 'approved_at', 'updated_at'])
    _sync_instance_from_record(instance, record)

    log_accounting_change(
        record,
        'rejected',
        actor=actor,
        stage=step.stage,
        details=comments or 'Approval step rejected.',
        old_values=previous,
        new_values=snapshot_accounting_object(instance, record.object_type),
    )
    sync_accounting_approval_to_platform_task(record)
    log_platform_audit_event(
        domain='finance',
        actor=actor,
        organization=record.entity.organization,
        entity=record.entity,
        event_type='accounting_approval.rejected',
        action='approval_rejected',
        resource_type='AccountingApprovalRecord',
        resource_id=str(record.id),
        subject_type=record.object_type,
        subject_id=str(record.object_id),
        resource_name=record.title,
        summary=f'{record.get_object_type_display()} rejected: {record.title}',
        diff={'before': previous, 'after': snapshot_accounting_object(instance, record.object_type)},
        context={'approval_status': record.status, 'stage': step.stage},
        metadata={'approval_record_id': record.id, 'comments': comments},
    )
    return record


def can_user_act_on_record(record, user):
    step = _current_pending_step(record)
    if not step:
        return False
    try:
        _authorize_record_step(record, step, user)
        return True
    except ValueError:
        return False


def build_accounting_inbox_items(user, entity=None):
    records = AccountingApprovalRecord.objects.select_related('entity', 'requested_by', 'approved_by').prefetch_related(
        'steps__assigned_role', 'steps__assigned_staff', 'steps__acted_by', 'change_logs__actor'
    )
    if entity is not None:
        records = records.filter(entity=entity)
    records = records.filter(status__in=['pending_review', 'pending_approval', 'approved', 'rejected'])

    items = []
    for record in records:
        if record.entity_id and entity is not None and record.entity_id != entity.id:
            continue
        if record.status in ['pending_review', 'pending_approval'] and not can_user_act_on_record(record, user):
            continue
        current_step = _current_pending_step(record)
        items.append({
            'id': record.id,
            'record_type': 'accounting_object',
            'object_type': record.object_type,
            'object_id': record.object_id,
            'title': record.title,
            'amount': str(record.amount),
            'status': record.status,
            'entity': record.entity_id,
            'entity_name': record.entity.name if record.entity else '',
            'requested_by': record.requested_by_id,
            'requested_by_name': record.requested_by.get_full_name() if record.requested_by else '',
            'submitted_at': record.submitted_at.isoformat() if record.submitted_at else None,
            'approved_at': record.approved_at.isoformat() if record.approved_at else None,
            'current_stage': current_step.stage if current_step else None,
            'can_approve': can_user_act_on_record(record, user),
            'steps': [
                {
                    'id': step.id,
                    'step_order': step.step_order,
                    'stage': step.stage,
                    'status': step.status,
                    'assigned_role': step.assigned_role_id,
                    'assigned_role_name': step.assigned_role.name if step.assigned_role else None,
                    'acted_by': step.acted_by_id,
                    'acted_by_name': step.acted_by.get_full_name() if step.acted_by else None,
                    'acted_at': step.acted_at.isoformat() if step.acted_at else None,
                    'comments': step.comments,
                }
                for step in record.steps.all().order_by('step_order')
            ],
            'change_logs': [
                {
                    'id': log.id,
                    'action': log.action,
                    'stage': log.stage,
                    'actor': log.actor_id,
                    'actor_name': log.actor.get_full_name() if log.actor else 'System',
                    'details': log.details,
                    'created_at': log.created_at.isoformat(),
                }
                for log in record.change_logs.all().order_by('-created_at')
            ],
        })
    return items