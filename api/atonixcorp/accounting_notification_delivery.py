from collections import defaultdict
from datetime import timedelta
from urllib.parse import urljoin

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags

from .models import Notification, NotificationPreference


DEFAULT_FRONTEND_BASE_URL = 'http://localhost:3000'
APPROVAL_OBJECT_LABELS = {
    'journal_entry': 'journal entry',
    'purchase_order': 'purchase order',
    'bill': 'bill',
    'bill_payment': 'bill payment',
    'payment': 'customer payment',
}


def _frontend_base_url():
    return (
        getattr(settings, 'APPROVAL_NOTIFICATION_BASE_URL', '')
        or getattr(settings, 'FRONTEND_BASE_URL', '')
        or DEFAULT_FRONTEND_BASE_URL
    )


def _email_brand_context():
    return {
        'email_brand_name': getattr(settings, 'EMAIL_BRAND_NAME', 'AtonixCorp'),
        'email_brand_title': getattr(settings, 'EMAIL_BRAND_TITLE', 'Institutional Finance Operations'),
        'email_brand_footer': getattr(
            settings,
            'EMAIL_BRAND_FOOTER',
            'AtonixCorp finance operations communications are designed for secure approval workflows, accountable execution, and institutional-grade control.',
        ),
        'email_support_email': getattr(settings, 'EMAIL_SUPPORT_EMAIL', ''),
        'email_support_url': getattr(settings, 'EMAIL_SUPPORT_URL', _frontend_base_url()),
    }


def _absolute_action_url(action_url):
    if not action_url:
        return ''
    if action_url.startswith('http://') or action_url.startswith('https://'):
        return action_url
    return urljoin(f"{_frontend_base_url().rstrip('/')}/", action_url.lstrip('/'))


def build_approval_action_url(*, related_content_type, entity_id=None, related_object_id=''):
    if entity_id:
        return f'/enterprise/entity/{entity_id}/approval-inbox?objectType={related_content_type}&objectId={related_object_id}'
    return f'/app/accounting/approval-inbox?objectType={related_content_type}&objectId={related_object_id}'


def approval_object_label(related_content_type):
    return APPROVAL_OBJECT_LABELS.get(related_content_type, 'approval item')


def approval_email_allowed(user):
    if not user:
        return False
    prefs, _ = NotificationPreference.objects.get_or_create(user=user)
    return prefs.email_approval_requests


def approval_in_app_allowed(user):
    if not user:
        return False
    prefs, _ = NotificationPreference.objects.get_or_create(user=user)
    return prefs.in_app_all


def create_in_app_approval_notification(*, user, organization, entity, title, message, related_content_type, related_object_id, action_url='', priority='high'):
    if not approval_in_app_allowed(user):
        return None
    resolved_action_url = action_url or build_approval_action_url(
        related_content_type=related_content_type,
        entity_id=getattr(entity, 'id', None),
        related_object_id=related_object_id,
    )
    return Notification.objects.create(
        user=user,
        organization=organization,
        notification_type='approval_request',
        priority=priority,
        title=title,
        message=message,
        related_entity=entity,
        related_content_type=related_content_type,
        related_object_id=str(related_object_id or ''),
        action_url=resolved_action_url,
    )


def send_approval_email(*, user, title, message, action_url='', related_content_type='', related_object_id='', entity=None):
    if not user or not getattr(user, 'email', '') or not approval_email_allowed(user):
        return 0

    resolved_action_url = action_url or build_approval_action_url(
        related_content_type=related_content_type,
        entity_id=getattr(entity, 'id', None),
        related_object_id=related_object_id,
    )
    absolute_action_url = _absolute_action_url(resolved_action_url)
    context = {
        'recipient_name': user.get_full_name() or user.username or user.email,
        'title': title,
        'message': message,
        'action_url': absolute_action_url,
        'action_label': f"Review {approval_object_label(related_content_type)}",
        'object_label': approval_object_label(related_content_type).title(),
        'entity_name': entity.name if entity else '',
        'related_object_id': related_object_id,
    }
    context.update(_email_brand_context())
    html_body = render_to_string('email/approval_request.html', context)
    text_body = strip_tags(html_body)
    email = EmailMultiAlternatives(
        subject=title,
        body=text_body,
        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@atonixcorp.local'),
        to=[user.email],
    )
    email.attach_alternative(html_body, 'text/html')
    return email.send(fail_silently=False)


def dispatch_approval_request_notifications(*, users, organization, entity, title, message, related_content_type, related_object_id, action_url='', priority='high'):
    created_notifications = []
    emailed_user_ids = []
    seen_user_ids = set()

    for user in users:
        if not user or user.id in seen_user_ids:
            continue
        seen_user_ids.add(user.id)
        notification = create_in_app_approval_notification(
            user=user,
            organization=organization,
            entity=entity,
            title=title,
            message=message,
            related_content_type=related_content_type,
            related_object_id=related_object_id,
            action_url=action_url,
            priority=priority,
        )
        if notification:
            created_notifications.append(notification)
        if send_approval_email(
            user=user,
            title=title,
            message=message,
            action_url=action_url,
            related_content_type=related_content_type,
            related_object_id=related_object_id,
            entity=entity,
        ):
            emailed_user_ids.append(user.id)

    return {
        'notifications': created_notifications,
        'emailed_user_ids': emailed_user_ids,
    }


def send_approval_digest(*, hours=24, users=None):
    since = timezone.now() - timedelta(hours=hours)
    notifications = Notification.objects.filter(
        notification_type='approval_request',
        status='unread',
        sent_at__gte=since,
    ).select_related('user', 'related_entity').order_by('user_id', '-sent_at')

    if users is not None:
        user_ids = [user.id for user in users if user]
        notifications = notifications.filter(user_id__in=user_ids)

    grouped = defaultdict(list)
    for notification in notifications:
        grouped[notification.user].append(notification)

    deliveries = []
    for user, items in grouped.items():
        if not approval_email_allowed(user):
            continue
        lines = []
        html_items = []
        for item in items[:20]:
            entity_name = item.related_entity.name if item.related_entity else 'Unknown entity'
            action_url = _absolute_action_url(
                item.action_url or build_approval_action_url(
                    related_content_type=item.related_content_type,
                    entity_id=item.related_entity_id,
                    related_object_id=item.related_object_id,
                )
            )
            lines.append(f"- [{entity_name}] {item.title}: {item.message} ({action_url})")
            html_items.append({
                'entity_name': entity_name,
                'title': item.title,
                'message': item.message,
                'action_url': action_url,
                'action_label': f"Review {approval_object_label(item.related_content_type)}",
            })
        if len(items) > 20:
            lines.append(f"- ...and {len(items) - 20} more approval requests")
        digest_url = _absolute_action_url('/app/accounting/approval-inbox')
        context = {
            'recipient_name': user.get_full_name() or user.username or user.email,
            'notification_count': len(items),
            'items': html_items,
            'digest_url': digest_url,
        }
        context.update(_email_brand_context())
        html_body = render_to_string('email/approval_digest.html', context)
        text_body = strip_tags(html_body)
        email = EmailMultiAlternatives(
            subject=f"Finance approval digest ({len(items)} pending)",
            body=text_body,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@atonixcorp.local'),
            to=[user.email],
        )
        email.attach_alternative(html_body, 'text/html')
        sent = email.send(fail_silently=False)
        deliveries.append({'user_id': user.id, 'notification_count': len(items), 'sent_count': sent})
    return deliveries
