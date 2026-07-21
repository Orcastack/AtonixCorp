from decimal import Decimal

from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .accounting_notification_delivery import build_approval_action_url, dispatch_approval_request_notifications
from .models import (
    EntityStaff,
    JournalApprovalDelegation,
    JournalApprovalMatrix,
    JournalEntry,
    JournalEntryApprovalStep,
    JournalEntryChangeLog,
    LedgerPeriod,
    Notification,
)
from .platform_foundation import log_platform_audit_event, sync_journal_entry_approval_task


def snapshot_journal_entry(entry):
    return {
        'id': entry.id,
        'entity': entry.entity_id,
        'entry_type': entry.entry_type,
        'reference_number': entry.reference_number,
        'description': entry.description,
        'posting_date': entry.posting_date.isoformat() if entry.posting_date else None,
        'memo': entry.memo,
        'amount_total': str(entry.amount_total or '0'),
        'status': entry.status,
        'created_by': entry.created_by_id,
        'approved_by': entry.approved_by_id,
        'approved_at': entry.approved_at.isoformat() if entry.approved_at else None,
        'submitted_at': entry.submitted_at.isoformat() if entry.submitted_at else None,
    }


def log_journal_change(entry, action, actor=None, stage='', details='', old_values=None, new_values=None):
    return JournalEntryChangeLog.objects.create(
        journal_entry=entry,
        entity=entry.entity,
        actor=actor,
        action=action,
        stage=stage,
        details=details,
        old_values=old_values or {},
        new_values=new_values or {},
    )


def get_locked_period(entity, posting_date):
    if not entity or not posting_date:
        return None

    return LedgerPeriod.objects.filter(
        entity=entity,
        start_date__lte=posting_date,
        end_date__gte=posting_date,
    ).filter(
        Q(status='closed') | Q(no_posting_after__isnull=False, no_posting_after__gte=posting_date)
    ).order_by('-end_date').first()


def ensure_period_is_open(entity, posting_date, entry=None, actor=None):
    locked_period = get_locked_period(entity, posting_date)
    if not locked_period:
        return

    if entry is not None:
        log_journal_change(
            entry,
            'period_locked',
            actor=actor,
            details=f'Posting date {posting_date} falls in locked period {locked_period.period_name}.',
            new_values={
                'period': locked_period.period_name,
                'status': locked_period.status,
                'no_posting_after': locked_period.no_posting_after.isoformat() if locked_period.no_posting_after else None,
            },
        )
    raise ValueError(f'Posting date {posting_date} falls in locked period {locked_period.period_name}.')


def get_staff_for_user(entity, user):
    if not entity or not user or not user.is_authenticated:
        return None
    return EntityStaff.objects.filter(entity=entity, user=user, status='active').select_related('role').first()


def user_has_role(entity, user, role):
    if role is None:
        return True
    staff_member = get_staff_for_user(entity, user)
    return bool(staff_member and staff_member.role_id == role.id)


def get_matching_approval_matrix(entry):
    matrices = JournalApprovalMatrix.objects.filter(entity=entry.entity, is_active=True).select_related(
        'preparer_role', 'reviewer_role', 'approver_role'
    )
    applicable = []
    amount = Decimal(entry.amount_total or '0')
    for matrix in matrices:
        if matrix.entry_type and matrix.entry_type != entry.entry_type:
            continue
        if amount < (matrix.minimum_amount or Decimal('0')):
            continue
        if matrix.maximum_amount is not None and amount > matrix.maximum_amount:
            continue
        applicable.append(matrix)

    if not applicable:
        return None

    applicable.sort(
        key=lambda matrix: (
            1 if matrix.entry_type else 0,
            matrix.minimum_amount or Decimal('0'),
            0 if matrix.maximum_amount is None else -(matrix.maximum_amount),
            matrix.updated_at.timestamp() if matrix.updated_at else 0,
            matrix.id or 0,
        ),
        reverse=True,
    )
    return applicable[0]


def _current_pending_step(entry):
    return entry.approval_steps.filter(status='pending').order_by('step_order').first()


def _actor_ids_in_workflow(entry):
    actor_ids = set()
    if entry.created_by_id:
        actor_ids.add(entry.created_by_id)
    actor_ids.update(
        entry.approval_steps.exclude(acted_by_id__isnull=True).values_list('acted_by_id', flat=True)
    )
    return actor_ids


def _find_active_delegation(entry, step, actor):
    staff_member = get_staff_for_user(entry.entity, actor)
    if not staff_member:
        return None

    today = timezone.now().date()
    amount = Decimal(entry.amount_total or '0')
    delegations = JournalApprovalDelegation.objects.filter(
        entity=entry.entity,
        delegate=staff_member,
        stage=step.stage,
        is_active=True,
        start_date__lte=today,
        end_date__gte=today,
    ).select_related('delegator__role')

    for delegation in delegations:
        if step.assigned_role_id and delegation.delegator.role_id != step.assigned_role_id:
            continue
        if amount < (delegation.minimum_amount or Decimal('0')):
            continue
        if delegation.maximum_amount is not None and amount > delegation.maximum_amount:
            continue
        return delegation
    return None


def _validate_matrix(entry, matrix):
    if matrix is None:
        raise ValueError('No active approval matrix matches this journal entry. Configure a matrix before submitting.')

    if matrix.preparer_role and not user_has_role(entry.entity, entry.created_by, matrix.preparer_role):
        raise ValueError('The journal preparer does not satisfy the configured preparer role.')

    if matrix.require_reviewer and not matrix.reviewer_role:
        raise ValueError('The approval matrix requires a reviewer role.')

    if matrix.require_approver and not matrix.approver_role:
        raise ValueError('The approval matrix requires an approver role.')


def _deliver_journal_notifications(entry, step):
    if not step.assigned_role_id:
        return

    recipients = set(
        step.assigned_role.staff.filter(status='active').exclude(user_id__isnull=True).values_list('user_id', flat=True)
    )
    today = timezone.now().date()
    delegations = JournalApprovalDelegation.objects.filter(
        entity=entry.entity,
        stage=step.stage,
        is_active=True,
        start_date__lte=today,
        end_date__gte=today,
        delegate__status='active',
    ).select_related('delegator__role', 'delegate__user')
    for delegation in delegations:
        if delegation.delegator.role_id != step.assigned_role_id:
            continue
        if delegation.delegate.user_id:
            recipients.add(delegation.delegate.user_id)

    dispatch_approval_request_notifications(
        users=User.objects.filter(id__in=recipients),
        organization=entry.entity.organization,
        entity=entry.entity,
        title='Journal approval required',
        message=f'{entry.reference_number} is awaiting {step.stage} approval.',
        related_content_type='journal_entry',
        related_object_id=entry.id,
        action_url=build_approval_action_url(
            related_content_type='journal_entry',
            entity_id=entry.entity_id,
            related_object_id=entry.id,
        ),
    )


@transaction.atomic
def submit_journal_entry(entry, actor):
    if entry.status not in ['draft', 'rejected']:
        raise ValueError('Only draft or rejected journal entries can be submitted.')

    ensure_period_is_open(entry.entity, entry.posting_date, entry=entry, actor=actor)
    matrix = get_matching_approval_matrix(entry)
    _validate_matrix(entry, matrix)

    entry.approval_steps.all().delete()

    created_staff = get_staff_for_user(entry.entity, entry.created_by)
    JournalEntryApprovalStep.objects.create(
        journal_entry=entry,
        step_order=1,
        stage='preparer',
        assigned_role=matrix.preparer_role,
        assigned_staff=created_staff,
        status='approved',
        acted_by=entry.created_by,
        acted_at=timezone.now(),
        comments='Prepared and submitted.',
    )

    step_order = 2
    pending_status = 'pending_approval'
    if matrix.require_reviewer:
        JournalEntryApprovalStep.objects.create(
            journal_entry=entry,
            step_order=step_order,
            stage='reviewer',
            assigned_role=matrix.reviewer_role,
            status='pending',
        )
        step_order += 1
        pending_status = 'pending_review'

    if matrix.require_approver:
        JournalEntryApprovalStep.objects.create(
            journal_entry=entry,
            step_order=step_order,
            stage='approver',
            assigned_role=matrix.approver_role,
            status='pending',
        )

    previous = snapshot_journal_entry(entry)
    entry.submitted_at = timezone.now()
    entry.status = pending_status
    entry.approved_by = None
    entry.approved_at = None
    entry.save(update_fields=['submitted_at', 'status', 'approved_by', 'approved_at', 'updated_at'])

    log_journal_change(
        entry,
        'matrix_applied',
        actor=actor,
        details=f'Applied matrix {matrix.name}.',
        new_values={
            'matrix': matrix.name,
            'minimum_amount': str(matrix.minimum_amount),
            'maximum_amount': str(matrix.maximum_amount) if matrix.maximum_amount is not None else None,
            'reviewer_role': matrix.reviewer_role.name if matrix.reviewer_role else None,
            'approver_role': matrix.approver_role.name if matrix.approver_role else None,
        },
    )
    log_journal_change(
        entry,
        'submitted',
        actor=actor,
        details='Journal entry submitted into the approval workflow.',
        old_values=previous,
        new_values=snapshot_journal_entry(entry),
    )
    sync_journal_entry_approval_task(entry)
    log_platform_audit_event(
        domain='finance',
        actor=actor,
        organization=entry.entity.organization,
        entity=entry.entity,
        event_type='journal_entry.submitted',
        action='approval_requested',
        resource_type='JournalEntry',
        resource_id=str(entry.id),
        subject_type='journal_entry',
        subject_id=str(entry.id),
        resource_name=entry.reference_number or entry.description or str(entry.id),
        summary=f'Journal entry submitted for approval: {entry.reference_number or entry.id}',
        diff={'before': previous, 'after': snapshot_journal_entry(entry)},
        context={'status': entry.status, 'stage': _current_pending_step(entry).stage if _current_pending_step(entry) else ''},
    )
    next_step = _current_pending_step(entry)
    if next_step:
        _deliver_journal_notifications(entry, next_step)
    return entry


def _authorize_step(entry, step, actor):
    if actor.id == entry.created_by_id and step.stage in ['reviewer', 'approver']:
        raise ValueError('Segregation of duties prevents the preparer from approving this journal entry.')

    prior_actor_ids = _actor_ids_in_workflow(entry)
    if actor.id in prior_actor_ids and step.stage == 'approver':
        raise ValueError('Segregation of duties requires a different approver than earlier workflow actors.')

    if step.assigned_role and user_has_role(entry.entity, actor, step.assigned_role):
        return None

    delegation = _find_active_delegation(entry, step, actor)
    if delegation:
        return delegation

    raise ValueError('You are not authorized to act on the current approval step.')


@transaction.atomic
def approve_journal_entry(entry, actor, comments=''):
    if entry.status not in ['pending_review', 'pending_approval']:
        raise ValueError('This journal entry is not awaiting approval.')

    ensure_period_is_open(entry.entity, entry.posting_date, entry=entry, actor=actor)
    step = _current_pending_step(entry)
    if not step:
        raise ValueError('No pending approval step was found for this journal entry.')

    delegation = _authorize_step(entry, step, actor)
    previous = snapshot_journal_entry(entry)
    step.status = 'approved'
    step.acted_by = actor
    step.acted_at = timezone.now()
    step.comments = comments or step.comments
    step.delegated_from = delegation
    step.save(update_fields=['status', 'acted_by', 'acted_at', 'comments', 'delegated_from', 'updated_at'])

    next_step = _current_pending_step(entry)
    if next_step and next_step.stage == 'approver':
        entry.status = 'pending_approval'
        entry.save(update_fields=['status', 'updated_at'])
        _deliver_journal_notifications(entry, next_step)
    elif next_step:
        entry.status = 'pending_review'
        entry.save(update_fields=['status', 'updated_at'])
        _deliver_journal_notifications(entry, next_step)
    else:
        entry.status = 'posted'
        entry.approved_by = actor
        entry.approved_at = timezone.now()
        entry.save(update_fields=['status', 'approved_by', 'approved_at', 'updated_at'])

    log_journal_change(
        entry,
        'approved',
        actor=actor,
        stage=step.stage,
        details='Delegated authority exercised.' if delegation else 'Approval step completed.',
        old_values=previous,
        new_values=snapshot_journal_entry(entry),
    )
    sync_journal_entry_approval_task(entry)
    log_platform_audit_event(
        domain='finance',
        actor=actor,
        organization=entry.entity.organization,
        entity=entry.entity,
        event_type='journal_entry.approved',
        action='journal_posted' if entry.status == 'posted' else 'approval_progressed',
        resource_type='JournalEntry',
        resource_id=str(entry.id),
        subject_type='journal_entry',
        subject_id=str(entry.id),
        resource_name=entry.reference_number or entry.description or str(entry.id),
        summary=f'Journal entry approval updated: {entry.reference_number or entry.id}',
        diff={'before': previous, 'after': snapshot_journal_entry(entry)},
        context={'status': entry.status, 'stage': step.stage},
        metadata={'comments': comments},
    )
    return entry


@transaction.atomic
def reject_journal_entry(entry, actor, comments=''):
    if entry.status not in ['pending_review', 'pending_approval']:
        raise ValueError('This journal entry is not awaiting approval.')

    step = _current_pending_step(entry)
    if not step:
        raise ValueError('No pending approval step was found for this journal entry.')

    _authorize_step(entry, step, actor)
    previous = snapshot_journal_entry(entry)
    step.status = 'rejected'
    step.acted_by = actor
    step.acted_at = timezone.now()
    step.comments = comments or step.comments
    step.save(update_fields=['status', 'acted_by', 'acted_at', 'comments', 'updated_at'])

    entry.status = 'rejected'
    entry.approved_by = None
    entry.approved_at = None
    entry.save(update_fields=['status', 'approved_by', 'approved_at', 'updated_at'])

    log_journal_change(
        entry,
        'rejected',
        actor=actor,
        stage=step.stage,
        details=comments or 'Approval step rejected.',
        old_values=previous,
        new_values=snapshot_journal_entry(entry),
    )
    sync_journal_entry_approval_task(entry)
    log_platform_audit_event(
        domain='finance',
        actor=actor,
        organization=entry.entity.organization,
        entity=entry.entity,
        event_type='journal_entry.rejected',
        action='approval_rejected',
        resource_type='JournalEntry',
        resource_id=str(entry.id),
        subject_type='journal_entry',
        subject_id=str(entry.id),
        resource_name=entry.reference_number or entry.description or str(entry.id),
        summary=f'Journal entry rejected: {entry.reference_number or entry.id}',
        diff={'before': previous, 'after': snapshot_journal_entry(entry)},
        context={'status': entry.status, 'stage': step.stage},
        metadata={'comments': comments},
    )
    return entry


def can_user_act_on_journal(entry, user):
    step = _current_pending_step(entry)
    if not step:
        return False
    try:
        _authorize_step(entry, step, user)
        return True
    except ValueError:
        return False


def build_journal_inbox_items(user, entity=None):
    entries = JournalEntry.objects.select_related('entity', 'created_by', 'approved_by').prefetch_related(
        'approval_steps__assigned_role', 'approval_steps__assigned_staff', 'approval_steps__acted_by', 'change_logs__actor'
    ).filter(status__in=['pending_review', 'pending_approval', 'posted', 'rejected'])
    if entity is not None:
        entries = entries.filter(entity=entity)

    items = []
    for entry in entries:
        if entry.status in ['pending_review', 'pending_approval'] and not can_user_act_on_journal(entry, user):
            continue
        current_step = _current_pending_step(entry)
        items.append({
            'id': entry.id,
            'record_type': 'journal_entry',
            'object_type': 'journal_entry',
            'object_id': entry.id,
            'title': entry.reference_number,
            'description': entry.description,
            'amount': str(entry.amount_total or '0'),
            'status': entry.status,
            'entity': entry.entity_id,
            'entity_name': entry.entity.name if entry.entity else '',
            'requested_by': entry.created_by_id,
            'requested_by_name': entry.created_by.get_full_name() if entry.created_by else '',
            'submitted_at': entry.submitted_at.isoformat() if entry.submitted_at else None,
            'approved_at': entry.approved_at.isoformat() if entry.approved_at else None,
            'current_stage': current_step.stage if current_step else None,
            'can_approve': can_user_act_on_journal(entry, user),
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
                for step in entry.approval_steps.all().order_by('step_order')
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
                for log in entry.change_logs.all().order_by('-created_at')
            ],
        })
    return items