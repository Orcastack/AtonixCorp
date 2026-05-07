from __future__ import annotations

import json
from datetime import date, datetime
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.mail import send_mail
from django.utils.dateparse import parse_date
from django.utils import timezone

from finances.models import Notification, NotificationPreference

from .documents import build_scenario_report_pdf, ensure_certificate_pdf, ensure_grant_package_pdf
from .models import (
    DeliveryChannel,
    DeliveryStatus,
    EquityDeliveryLog,
    EquityExerciseRequest,
    EquityExternalAdapterConfig,
    EquityGrant,
    EquityPayrollTaxEvent,
    EquityScenarioApprovalPolicy,
    EquityScenarioApproval,
    EquityShareCertificate,
    EquityVestingEvent,
    ExternalAdapterType,
    PayrollSyncStatus,
)


DEFAULT_TIMEOUT_SECONDS = 10


def _serialize_date(value) -> str:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    parsed = parse_date(str(value))
    return parsed.isoformat() if parsed else str(value)


def _unique_recipients(users: Iterable, fallback_emails: Iterable[str] | None = None) -> list[tuple[object | None, str]]:
    recipients = []
    seen = set()

    for user in users or []:
        if not user:
            continue
        email = getattr(user, 'email', '') or ''
        marker = email.lower() or f'user:{getattr(user, "id", None)}'
        if marker in seen:
            continue
        seen.add(marker)
        recipients.append((user, email))

    for email in fallback_emails or []:
        clean_email = (email or '').strip()
        if not clean_email:
            continue
        marker = clean_email.lower()
        if marker in seen:
            continue
        seen.add(marker)
        recipients.append((None, clean_email))

    return recipients


def _email_allowed(user, event_name: str) -> bool:
    if not user:
        return True
    prefs, _ = NotificationPreference.objects.get_or_create(user=user)
    if event_name in {'exercise_submitted', 'exercise_approved', 'exercise_rejected'}:
        return prefs.email_approval_requests
    if event_name in {'vesting_milestone'}:
        return prefs.email_deadline_reminders
    if event_name in {'payment_sync_failed'}:
        return prefs.email_payment_due
    return True


def _in_app_allowed(user) -> bool:
    if not user:
        return False
    prefs, _ = NotificationPreference.objects.get_or_create(user=user)
    return prefs.in_app_all


def _log_delivery(**kwargs) -> EquityDeliveryLog:
    return EquityDeliveryLog.objects.create(**kwargs)


def _record_in_app_notification(*, workspace, user, title: str, message: str, action_url: str = '', grant=None, vesting_event=None, exercise_request=None, certificate=None, payroll_tax_event=None, priority: str = 'medium', notification_type: str = 'system') -> EquityDeliveryLog | None:
    if not user or not _in_app_allowed(user):
        return None

    notification = Notification.objects.create(
        user=user,
        organization=workspace.organization,
        notification_type=notification_type,
        priority=priority,
        title=title,
        message=message,
        related_entity=workspace,
        related_content_type='equity',
        related_object_id=str(
            getattr(certificate, 'id', None)
            or getattr(exercise_request, 'id', None)
            or getattr(vesting_event, 'id', None)
            or getattr(grant, 'id', None)
            or getattr(payroll_tax_event, 'id', None)
            or ''
        ),
        action_url=action_url,
    )
    return _log_delivery(
        workspace=workspace,
        grant=grant,
        vesting_event=vesting_event,
        exercise_request=exercise_request,
        certificate=certificate,
        payroll_tax_event=payroll_tax_event,
        recipient_user=user,
        recipient_email=user.email or '',
        channel=DeliveryChannel.IN_APP,
        event_name=notification_type,
        status=DeliveryStatus.SENT,
        subject=title,
        message=message,
        provider_response={'notification_id': notification.id, 'action_url': action_url},
        delivered_at=timezone.now(),
    )


def _record_email_delivery(*, workspace, recipient_user, recipient_email: str, title: str, message: str, event_name: str, document_payload: dict | None = None, grant=None, vesting_event=None, exercise_request=None, certificate=None, payroll_tax_event=None) -> EquityDeliveryLog | None:
    if not recipient_email or (recipient_user and not _email_allowed(recipient_user, event_name)):
        return None

    delivery = _log_delivery(
        workspace=workspace,
        grant=grant,
        vesting_event=vesting_event,
        exercise_request=exercise_request,
        certificate=certificate,
        payroll_tax_event=payroll_tax_event,
        recipient_user=recipient_user,
        recipient_email=recipient_email,
        channel=DeliveryChannel.EMAIL,
        event_name=event_name,
        status=DeliveryStatus.QUEUED,
        subject=title,
        message=message,
        document_payload=document_payload or {},
    )
    try:
        sent = send_mail(
            subject=title,
            message=message,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@ledgora.local'),
            recipient_list=[recipient_email],
            fail_silently=False,
        )
        delivery.status = DeliveryStatus.SENT if sent else DeliveryStatus.FAILED
        delivery.provider_response = {'sent_count': sent}
        delivery.delivered_at = timezone.now() if sent else None
        delivery.error_message = '' if sent else 'Email backend returned zero sent messages.'
    except Exception as exc:
        delivery.status = DeliveryStatus.FAILED
        delivery.error_message = str(exc)
        delivery.provider_response = {'error_type': exc.__class__.__name__}
    delivery.save(update_fields=['status', 'provider_response', 'delivered_at', 'error_message', 'updated_at'])
    return delivery


def _record_document_delivery(*, workspace, recipient_user, recipient_email: str, title: str, message: str, event_name: str, document_payload: dict, document_file_name: str = '', document_bytes: bytes | None = None, grant=None, vesting_event=None, exercise_request=None, certificate=None, payroll_tax_event=None) -> EquityDeliveryLog:
    delivery = _log_delivery(
        workspace=workspace,
        grant=grant,
        vesting_event=vesting_event,
        exercise_request=exercise_request,
        certificate=certificate,
        payroll_tax_event=payroll_tax_event,
        recipient_user=recipient_user,
        recipient_email=recipient_email,
        channel=DeliveryChannel.DOCUMENT,
        event_name=event_name,
        status=DeliveryStatus.SENT,
        subject=title,
        message=message,
        document_payload=document_payload,
        delivered_at=timezone.now(),
    )
    if document_bytes and document_file_name:
        delivery.document_file.save(document_file_name, ContentFile(document_bytes), save=False)
    elif certificate and certificate.pdf_file:
        delivery.document_file = certificate.pdf_file.name
    elif grant and grant.grant_package_file:
        delivery.document_file = grant.grant_package_file.name
    if delivery.document_file:
        delivery.save(update_fields=['document_file', 'updated_at'])
    return delivery


def dispatch_equity_delivery(*, workspace, event_name: str, title: str, message: str, recipients: Iterable, fallback_emails: Iterable[str] | None = None, action_url: str = '', grant=None, vesting_event=None, exercise_request=None, certificate=None, payroll_tax_event=None, priority: str = 'medium', notification_type: str = 'system', include_document: bool = False, document_payload: dict | None = None, document_file_name: str = '', document_bytes: bytes | None = None) -> list[EquityDeliveryLog]:
    logs: list[EquityDeliveryLog] = []
    for recipient_user, recipient_email in _unique_recipients(recipients, fallback_emails):
        in_app_log = _record_in_app_notification(
            workspace=workspace,
            user=recipient_user,
            title=title,
            message=message,
            action_url=action_url,
            grant=grant,
            vesting_event=vesting_event,
            exercise_request=exercise_request,
            certificate=certificate,
            payroll_tax_event=payroll_tax_event,
            priority=priority,
            notification_type=notification_type,
        )
        if in_app_log:
            logs.append(in_app_log)

        email_log = _record_email_delivery(
            workspace=workspace,
            recipient_user=recipient_user,
            recipient_email=recipient_email,
            title=title,
            message=message,
            event_name=event_name,
            document_payload=document_payload,
            grant=grant,
            vesting_event=vesting_event,
            exercise_request=exercise_request,
            certificate=certificate,
            payroll_tax_event=payroll_tax_event,
        )
        if email_log:
            logs.append(email_log)

        if include_document and document_payload:
            logs.append(
                _record_document_delivery(
                    workspace=workspace,
                    recipient_user=recipient_user,
                    recipient_email=recipient_email,
                    title=title,
                    message=message,
                    event_name=event_name,
                    document_payload=document_payload,
                    document_file_name=document_file_name,
                    document_bytes=document_bytes,
                    grant=grant,
                    vesting_event=vesting_event,
                    exercise_request=exercise_request,
                    certificate=certificate,
                    payroll_tax_event=payroll_tax_event,
                )
            )
    return logs


def _scenario_action_url(approval: EquityScenarioApproval) -> str:
    return f'/app/equity/{approval.workspace_id}/scenarios'


def _scenario_document_payload(approval: EquityScenarioApproval) -> dict:
    return {
        'approval_id': str(approval.id),
        'title': approval.title,
        'reporting_period': approval.reporting_period,
        'status': approval.status,
        'board_status': approval.board_status,
        'legal_status': approval.legal_status,
    }


def _scenario_document_file(approval: EquityScenarioApproval) -> tuple[str, bytes]:
    pdf_bytes = build_scenario_report_pdf(
        approval.title,
        f"{approval.workspace.name} · {approval.reporting_period or 'Scenario Approval'}",
        approval.analysis_payload,
    )
    filename = f"{approval.title.lower().replace(' ', '-')}-{approval.status}.pdf"
    return filename, pdf_bytes


def notify_scenario_requested(approval: EquityScenarioApproval, board_reviewers, legal_reviewers):
    title = f'Scenario approval requested: {approval.title}'
    message = f'{approval.requested_by.get_full_name() or approval.requested_by.username if approval.requested_by else "A user"} requested approval for {approval.title}. Board and legal review are now pending.'
    document_file_name, document_bytes = _scenario_document_file(approval)
    dispatch_equity_delivery(
        workspace=approval.workspace,
        event_name='scenario_approval_requested',
        title=title,
        message=message,
        recipients=[approval.requested_by, *board_reviewers, *legal_reviewers],
        action_url=_scenario_action_url(approval),
        priority='high',
        notification_type='approval_request',
        include_document=True,
        document_payload=_scenario_document_payload(approval),
        document_file_name=document_file_name,
        document_bytes=document_bytes,
    )


def notify_scenario_review_decision(approval: EquityScenarioApproval, *, reviewer_type: str, approved: bool):
    decision = 'approved' if approved else 'rejected'
    title = f'{reviewer_type.title()} {decision}: {approval.title}'
    message = f'{approval.title} was {decision} by {reviewer_type}. Current status is {approval.status}.'
    recipients = [approval.requested_by, approval.board_approved_by, approval.legal_approved_by]
    document_file_name, document_bytes = _scenario_document_file(approval)
    dispatch_equity_delivery(
        workspace=approval.workspace,
        event_name=f'scenario_{reviewer_type}_{decision}',
        title=title,
        message=message,
        recipients=recipients,
        action_url=_scenario_action_url(approval),
        priority='high' if not approved else 'medium',
        notification_type='approval_request',
        include_document=True,
        document_payload=_scenario_document_payload(approval),
        document_file_name=document_file_name,
        document_bytes=document_bytes,
    )


def notify_scenario_committed(approval: EquityScenarioApproval):
    title = f'Scenario committed: {approval.title}'
    message = f'{approval.title} has been committed to the live cap table as {approval.committed_round.name if approval.committed_round else "a funding round"}.'
    document_file_name, document_bytes = _scenario_document_file(approval)
    dispatch_equity_delivery(
        workspace=approval.workspace,
        event_name='scenario_committed',
        title=title,
        message=message,
        recipients=[approval.requested_by, approval.board_approved_by, approval.legal_approved_by],
        action_url=_scenario_action_url(approval),
        priority='high',
        notification_type='system',
        include_document=True,
        document_payload=_scenario_document_payload(approval),
        document_file_name=document_file_name,
        document_bytes=document_bytes,
    )


def _scenario_review_recipients(approval: EquityScenarioApproval, reviewer_type: str, *, escalated: bool = False):
    policy = EquityScenarioApprovalPolicy.objects.filter(workspace=approval.workspace).first()
    if not policy:
        return [approval.requested_by, getattr(approval.workspace.organization, 'owner', None)]

    if reviewer_type == 'board':
        staff_queryset = policy.board_escalation_reviewers.all() if escalated and policy.board_escalation_reviewers.exists() else policy.board_reviewers.all()
    else:
        staff_queryset = policy.legal_escalation_reviewers.all() if escalated and policy.legal_escalation_reviewers.exists() else policy.legal_reviewers.all()

    recipients = [approval.requested_by]
    recipients.extend(staff.user for staff in staff_queryset.select_related('user') if staff.user_id)
    if not staff_queryset.exists():
        recipients.append(getattr(approval.workspace.organization, 'owner', None))
    return recipients


def notify_scenario_reminder(approval: EquityScenarioApproval, *, reviewer_type: str, escalated: bool = False):
    title = f'{reviewer_type.title()} review overdue: {approval.title}' if escalated else f'{reviewer_type.title()} review due: {approval.title}'
    message = (
        f'{approval.title} is still pending {reviewer_type} review and has crossed its SLA deadline.'
        if escalated
        else f'{approval.title} is pending {reviewer_type} review and has reached its SLA deadline.'
    )
    document_file_name, document_bytes = _scenario_document_file(approval)
    dispatch_equity_delivery(
        workspace=approval.workspace,
        event_name=f'scenario_{reviewer_type}_sla_reminder',
        title=title,
        message=message,
        recipients=_scenario_review_recipients(approval, reviewer_type, escalated=escalated),
        action_url=_scenario_action_url(approval),
        priority='high',
        notification_type='approval_request',
        include_document=True,
        document_payload=_scenario_document_payload(approval),
        document_file_name=document_file_name,
        document_bytes=document_bytes,
    )


def notify_scenario_escalated(approval: EquityScenarioApproval, *, reviewer_type: str):
    notify_scenario_reminder(approval, reviewer_type=reviewer_type, escalated=True)


def _adapter_url(config: EquityExternalAdapterConfig) -> str:
    base_url = config.base_url.rstrip('/') + '/'
    endpoint_path = (config.endpoint_path or '').lstrip('/')
    return urljoin(base_url, endpoint_path)


def _build_adapter_headers(config: EquityExternalAdapterConfig) -> dict:
    headers = {'Content-Type': 'application/json'}
    headers.update(config.default_headers or {})
    if config.api_key:
        scheme = (config.auth_scheme or 'Bearer').strip()
        headers['Authorization'] = f'{scheme} {config.api_key}'.strip()
    return headers


def post_adapter_payload(config: EquityExternalAdapterConfig, payload: dict) -> dict:
    request = Request(
        _adapter_url(config),
        data=json.dumps(payload).encode('utf-8'),
        headers=_build_adapter_headers(config),
        method='POST',
    )
    timeout = int((config.adapter_settings or {}).get('timeout_seconds') or DEFAULT_TIMEOUT_SECONDS)
    try:
        with urlopen(request, timeout=timeout) as response:
            raw_body = response.read().decode('utf-8')
            parsed_body = json.loads(raw_body) if raw_body else {}
            return {
                'ok': 200 <= response.status < 300,
                'status': response.status,
                'body': parsed_body,
                'headers': dict(response.headers.items()),
            }
    except HTTPError as exc:
        body = exc.read().decode('utf-8') if hasattr(exc, 'read') else ''
        parsed_body = None
        try:
            parsed_body = json.loads(body) if body else {}
        except json.JSONDecodeError:
            parsed_body = {'raw': body}
        return {
            'ok': False,
            'status': exc.code,
            'body': parsed_body,
            'error': str(exc),
        }
    except URLError as exc:
        return {'ok': False, 'status': None, 'body': {}, 'error': str(exc)}


def test_external_adapter(config: EquityExternalAdapterConfig) -> dict:
    payload = {
        'event': 'adapter.healthcheck',
        'workspace_id': config.workspace_id,
        'provider_name': config.provider_name,
        'timestamp': timezone.now().isoformat(),
    }
    result = post_adapter_payload(config, payload)
    config.last_synced_at = timezone.now() if result.get('ok') else config.last_synced_at
    config.last_error = '' if result.get('ok') else result.get('error') or json.dumps(result.get('body') or {})
    config.save(update_fields=['last_synced_at', 'last_error', 'updated_at'])
    return result


def sync_payroll_tax_event(payroll_event: EquityPayrollTaxEvent) -> dict:
    configs = list(
        payroll_event.workspace.equity_adapter_configs.filter(adapter_type=ExternalAdapterType.PAYROLL, is_active=True)
    )
    payload = {
        'event': 'equity.payroll_tax',
        'workspace_id': payroll_event.workspace_id,
        'grant_id': str(payroll_event.grant_id or ''),
        'exercise_request_id': str(payroll_event.exercise_request_id or ''),
        'employee_id': payroll_event.staff.employee_id if payroll_event.staff_id else '',
        'gross_amount': str(payroll_event.gross_amount),
        'withholding_amount': str(payroll_event.withholding_amount),
        'tax_jurisdiction': payroll_event.tax_jurisdiction,
        'reference_number': payroll_event.reference_number,
        'details': payroll_event.details,
    }
    results = []
    successful = False
    for config in configs:
        result = post_adapter_payload(config, payload)
        results.append({'provider': config.provider_name, **result})
        config.last_synced_at = timezone.now() if result.get('ok') else config.last_synced_at
        config.last_error = '' if result.get('ok') else result.get('error') or json.dumps(result.get('body') or {})
        config.save(update_fields=['last_synced_at', 'last_error', 'updated_at'])
        _log_delivery(
            workspace=payroll_event.workspace,
            grant=payroll_event.grant,
            exercise_request=payroll_event.exercise_request,
            payroll_tax_event=payroll_event,
            channel=DeliveryChannel.WEBHOOK,
            event_name='payroll_adapter_sync',
            status=DeliveryStatus.SENT if result.get('ok') else DeliveryStatus.FAILED,
            subject=f'Payroll sync: {config.provider_name}',
            message='Payroll adapter sync completed.' if result.get('ok') else 'Payroll adapter sync failed.',
            provider_response={'provider': config.provider_name, **result},
            error_message=result.get('error', ''),
            delivered_at=timezone.now() if result.get('ok') else None,
        )
        successful = successful or bool(result.get('ok'))

    if configs:
        payroll_event.payroll_sync_status = PayrollSyncStatus.SYNCED if successful else PayrollSyncStatus.FAILED
        payroll_event.details = {**(payroll_event.details or {}), 'adapter_results': results}
        payroll_event.save(update_fields=['payroll_sync_status', 'details', 'updated_at'])

    return {
        'configured_adapters': len(configs),
        'successful': successful,
        'results': results,
    }


def sync_exercise_payment(exercise_request: EquityExerciseRequest) -> dict:
    configs = list(
        exercise_request.workspace.equity_adapter_configs.filter(adapter_type=ExternalAdapterType.PAYMENT, is_active=True)
    )
    payload = {
        'event': 'equity.exercise_payment',
        'workspace_id': exercise_request.workspace_id,
        'exercise_request_id': str(exercise_request.id),
        'grant_id': str(exercise_request.grant_id),
        'shareholder': exercise_request.shareholder.name,
        'requested_units': exercise_request.requested_units,
        'approved_units': exercise_request.approved_units,
        'strike_payment_amount': str(exercise_request.strike_payment_amount),
        'tax_withholding_amount': str(exercise_request.tax_withholding_amount),
        'payment_method': exercise_request.payment_method,
        'payment_status': exercise_request.payment_status,
        'notes': exercise_request.notes,
    }
    results = []
    successful = False
    for config in configs:
        result = post_adapter_payload(config, payload)
        results.append({'provider': config.provider_name, **result})
        config.last_synced_at = timezone.now() if result.get('ok') else config.last_synced_at
        config.last_error = '' if result.get('ok') else result.get('error') or json.dumps(result.get('body') or {})
        config.save(update_fields=['last_synced_at', 'last_error', 'updated_at'])
        _log_delivery(
            workspace=exercise_request.workspace,
            grant=exercise_request.grant,
            exercise_request=exercise_request,
            channel=DeliveryChannel.WEBHOOK,
            event_name='payment_adapter_sync',
            status=DeliveryStatus.SENT if result.get('ok') else DeliveryStatus.FAILED,
            subject=f'Payment sync: {config.provider_name}',
            message='Payment adapter sync completed.' if result.get('ok') else 'Payment adapter sync failed.',
            provider_response={'provider': config.provider_name, **result},
            error_message=result.get('error', ''),
            delivered_at=timezone.now() if result.get('ok') else None,
        )
        successful = successful or bool(result.get('ok'))
    return {
        'configured_adapters': len(configs),
        'successful': successful,
        'results': results,
    }


def notify_grant_issued(grant: EquityGrant) -> list[EquityDeliveryLog]:
    grant = ensure_grant_package_pdf(grant)
    recipients = [grant.employee.user] if grant.employee_id and grant.employee and grant.employee.user_id else []
    fallback_emails = [grant.shareholder.email]
    title = f'Grant issued: {grant.grant_number}'
    message = f'Your equity grant for {grant.total_units} units has been issued and is now available in your equity workspace.'
    document_payload = {
        'grant_number': grant.grant_number,
        'grant_type': grant.grant_type,
        'share_class': grant.share_class.name,
        'total_units': grant.total_units,
        'exercise_price': str(grant.exercise_price),
        'grant_date': _serialize_date(grant.grant_date),
        'vesting_start_date': _serialize_date(grant.vesting_start_date),
    }
    return dispatch_equity_delivery(
        workspace=grant.workspace,
        event_name='grant_issued',
        title=title,
        message=message,
        recipients=recipients,
        fallback_emails=fallback_emails,
        action_url=f'/app/equity/{grant.workspace_id}/me',
        grant=grant,
        priority='high',
        notification_type='system',
        include_document=True,
        document_payload=document_payload,
    )


def notify_vesting_milestone(vesting_event: EquityVestingEvent) -> list[EquityDeliveryLog]:
    grant = vesting_event.grant
    recipients = [grant.employee.user] if grant.employee_id and grant.employee and grant.employee.user_id else []
    fallback_emails = [grant.shareholder.email]
    title = f'Vesting milestone reached: {grant.grant_number}'
    message = f'{vesting_event.units} units vested on {_serialize_date(vesting_event.vest_date)} for grant {grant.grant_number}.'
    return dispatch_equity_delivery(
        workspace=grant.workspace,
        event_name='vesting_milestone',
        title=title,
        message=message,
        recipients=recipients,
        fallback_emails=fallback_emails,
        action_url=f'/app/equity/{grant.workspace_id}/me',
        grant=grant,
        vesting_event=vesting_event,
        priority='medium',
        notification_type='deadline_reminder',
        include_document=False,
    )


def notify_upcoming_vesting(vesting_event: EquityVestingEvent, days_until_vest: int) -> list[EquityDeliveryLog]:
    grant = vesting_event.grant
    recipients = [grant.employee.user] if grant.employee_id and grant.employee and grant.employee.user_id else []
    fallback_emails = [grant.shareholder.email]
    title = f'Upcoming vesting in {days_until_vest} day(s): {grant.grant_number}'
    message = f'{vesting_event.units} units are scheduled to vest on {_serialize_date(vesting_event.vest_date)} for grant {grant.grant_number}.'
    return dispatch_equity_delivery(
        workspace=grant.workspace,
        event_name=f'vesting_reminder_{days_until_vest}d',
        title=title,
        message=message,
        recipients=recipients,
        fallback_emails=fallback_emails,
        action_url=f'/app/equity/{grant.workspace_id}/me',
        grant=grant,
        vesting_event=vesting_event,
        priority='medium',
        notification_type='deadline_reminder',
    )


def notify_exercise_submitted(exercise_request: EquityExerciseRequest) -> list[EquityDeliveryLog]:
    logs: list[EquityDeliveryLog] = []
    requester_users = [exercise_request.created_by] if exercise_request.created_by_id else []
    logs.extend(
        dispatch_equity_delivery(
            workspace=exercise_request.workspace,
            event_name='exercise_submitted',
            title=f'Exercise submitted: {exercise_request.grant.grant_number}',
            message=f'Your request to exercise {exercise_request.requested_units} units has been submitted for approval.',
            recipients=requester_users,
            fallback_emails=[exercise_request.shareholder.email],
            action_url=f'/app/equity/{exercise_request.workspace_id}/me',
            grant=exercise_request.grant,
            exercise_request=exercise_request,
            priority='medium',
            notification_type='approval_request',
        )
    )
    approvers = [approval.approver for approval in exercise_request.approvals.select_related('approver')]
    logs.extend(
        dispatch_equity_delivery(
            workspace=exercise_request.workspace,
            event_name='exercise_submitted',
            title='Exercise approval requested',
            message=f'An equity exercise request for {exercise_request.requested_units} units requires your review.',
            recipients=approvers,
            action_url=f'/app/equity/{exercise_request.workspace_id}/exercises',
            grant=exercise_request.grant,
            exercise_request=exercise_request,
            priority='high',
            notification_type='approval_request',
        )
    )
    return logs


def notify_exercise_status(exercise_request: EquityExerciseRequest, *, approved: bool) -> list[EquityDeliveryLog]:
    title = 'Exercise approved' if approved else 'Exercise rejected'
    message = (
        f'Your request to exercise {exercise_request.approved_units or exercise_request.requested_units} units has been approved.'
        if approved
        else f'Your request to exercise {exercise_request.requested_units} units has been rejected.'
    )
    return dispatch_equity_delivery(
        workspace=exercise_request.workspace,
        event_name='exercise_approved' if approved else 'exercise_rejected',
        title=title,
        message=message,
        recipients=[exercise_request.created_by] if exercise_request.created_by_id else [],
        fallback_emails=[exercise_request.shareholder.email],
        action_url=f'/app/equity/{exercise_request.workspace_id}/me',
        grant=exercise_request.grant,
        exercise_request=exercise_request,
        priority='high' if approved else 'medium',
        notification_type='approval_request',
    )


def notify_certificate_released(certificate: EquityShareCertificate) -> list[EquityDeliveryLog]:
    certificate = ensure_certificate_pdf(certificate)
    grant = certificate.grant
    recipients = [grant.employee.user] if grant.employee_id and grant.employee and grant.employee.user_id else []
    fallback_emails = [certificate.issued_to.email]
    title = f'Certificate issued: {certificate.certificate_number}'
    message = f'Certificate {certificate.certificate_number} covering {certificate.issued_units} units is now available.'
    document_payload = certificate.certificate_payload or {
        'certificate_number': certificate.certificate_number,
        'grant_number': grant.grant_number,
        'issued_units': certificate.issued_units,
        'issue_date': _serialize_date(certificate.issue_date),
    }
    return dispatch_equity_delivery(
        workspace=certificate.workspace,
        event_name='certificate_release',
        title=title,
        message=message,
        recipients=recipients,
        fallback_emails=fallback_emails,
        action_url=f'/app/equity/{certificate.workspace_id}/me',
        grant=grant,
        certificate=certificate,
        priority='high',
        notification_type='system',
        include_document=True,
        document_payload=document_payload,
    )
