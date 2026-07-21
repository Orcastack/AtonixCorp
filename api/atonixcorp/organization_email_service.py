from calendar import monthrange
from datetime import datetime
from email.utils import make_msgid
from html import escape
from urllib.parse import quote

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.utils import timezone
from django.utils.html import strip_tags
from django.utils.text import slugify
from rest_framework.exceptions import ValidationError

from .models import (
    OrganizationEmailAccount,
    OrganizationEmailCampaign,
    OrganizationEmailDelivery,
    OrganizationEmailSubscription,
)
from .platform_foundation import log_platform_audit_event


TIER_LIMITS = {
    'basic': {'accounts': 0, 'monthly_sends': 250, 'campaigns': False},
    'professional': {'accounts': 5, 'monthly_sends': 2_500, 'campaigns': False},
    'enterprise': {'accounts': None, 'monthly_sends': 25_000, 'campaigns': True},
}


def _email_domain():
    return getattr(settings, 'ORGANIZATION_EMAIL_DOMAIN', 'atonixcorp.local').strip().lower()


def _subscription(organization):
    subscription, created = OrganizationEmailSubscription.objects.get_or_create(
        organization=organization,
        defaults={
            'tier': 'basic',
            'status': 'active',
            'monthly_send_limit': TIER_LIMITS['basic']['monthly_sends'],
        },
    )
    if created or subscription.monthly_send_limit != TIER_LIMITS[subscription.tier]['monthly_sends']:
        subscription.monthly_send_limit = TIER_LIMITS[subscription.tier]['monthly_sends']
        subscription.save(update_fields=['monthly_send_limit', 'updated_at'])
    return subscription


def subscription_summary(organization):
    subscription = _subscription(organization)
    limits = TIER_LIMITS[subscription.tier]
    month_start = timezone.make_aware(datetime(timezone.now().year, timezone.now().month, 1))
    sent_this_month = OrganizationEmailDelivery.objects.filter(
        organization=organization,
        status='sent',
        created_at__gte=month_start,
    ).count()
    return {
        'tier': subscription.tier,
        'status': subscription.status,
        'billing_reference': subscription.billing_reference,
        'monthly_send_limit': subscription.monthly_send_limit,
        'sent_this_month': sent_this_month,
        'remaining_sends': max(subscription.monthly_send_limit - sent_this_month, 0),
        'account_limit': limits['accounts'],
        'marketing_enabled': limits['campaigns'],
        'email_domain': _email_domain(),
    }


def set_subscription_tier(organization, tier, billing_reference=''):
    if tier not in TIER_LIMITS:
        raise ValidationError({'tier': 'Choose Basic, Professional, or Enterprise.'})
    subscription = _subscription(organization)
    subscription.tier = tier
    subscription.monthly_send_limit = TIER_LIMITS[tier]['monthly_sends']
    subscription.billing_reference = str(billing_reference or '').strip()
    subscription.status = 'active'
    subscription.save(update_fields=['tier', 'monthly_send_limit', 'billing_reference', 'status', 'updated_at'])
    return subscription


def provision_email_account(organization, actor, local_part, display_name=''):
    subscription = _subscription(organization)
    limits = TIER_LIMITS[subscription.tier]
    if subscription.status != 'active':
        raise ValidationError({'subscription': 'Email service is not active for this organization.'})
    if limits['accounts'] == 0:
        raise ValidationError({'subscription': 'Upgrade to Professional to provision workspace email accounts.'})
    if limits['accounts'] is not None and organization.email_accounts.filter(is_active=True).count() >= limits['accounts']:
        raise ValidationError({'subscription': 'The active email account limit for this tier has been reached.'})

    normalized_local_part = slugify(str(local_part or '').replace('@', '-')).replace('-', '.')
    if not normalized_local_part or len(normalized_local_part) > 64:
        raise ValidationError({'local_part': 'Use a valid email local part up to 64 characters.'})
    address = f'{normalized_local_part}@{slugify(organization.slug or organization.name)}.{_email_domain()}'
    account = OrganizationEmailAccount.objects.create(
        organization=organization,
        user=actor,
        local_part=normalized_local_part,
        address=address,
        display_name=str(display_name or organization.name).strip()[:160],
    )
    log_platform_audit_event(
        domain='email', event_type='email.account_provisioned', action='email_account_provisioned',
        actor=actor, organization=organization, resource_type='OrganizationEmailAccount',
        resource_id=str(account.id), resource_name=account.address,
        summary=f'Provisioned managed sender identity {account.address}',
        metadata={'tier': subscription.tier},
    )
    return account


def _validate_recipients(recipients):
    unique_recipients = []
    seen = set()
    for value in recipients or []:
        address = str(value or '').strip().lower()
        if not address or '@' not in address or address.startswith('@') or address.endswith('@'):
            raise ValidationError({'recipients': 'Each recipient must be a valid email address.'})
        if address not in seen:
            seen.add(address)
            unique_recipients.append(address)
    if not unique_recipients:
        raise ValidationError({'recipients': 'At least one recipient is required.'})
    return unique_recipients


def _remaining_sends(organization):
    return subscription_summary(organization)['remaining_sends']


def _unsubscribe_url(organization, recipient):
    base_url = getattr(settings, 'FRONTEND_BASE_URL', 'http://localhost:3000').rstrip('/')
    return f'{base_url}/email-preferences?organization={organization.id}&recipient={quote(recipient)}'


def _send_message(*, sender_address, recipient, subject, html_body, organization, campaign=None, event_type='campaign'):
    delivery = OrganizationEmailDelivery.objects.create(
        organization=organization,
        campaign=campaign,
        sender=campaign.sender if campaign else None,
        recipient=recipient,
        subject=subject,
        event_type=event_type,
        status='queued',
    )
    try:
        message = EmailMultiAlternatives(
            subject=subject,
            body=strip_tags(html_body),
            from_email=sender_address,
            to=[recipient],
            headers={'Message-ID': make_msgid(domain=_email_domain())},
        )
        message.attach_alternative(html_body, 'text/html')
        message.send(fail_silently=False)
        delivery.status = 'sent'
        delivery.sent_at = timezone.now()
        delivery.save(update_fields=['status', 'sent_at'])
    except Exception as error:
        delivery.status = 'failed'
        delivery.error_message = str(error)[:500]
        delivery.save(update_fields=['status', 'error_message'])
    return delivery


@transaction.atomic
def send_campaign(organization, actor, payload):
    subscription = _subscription(organization)
    campaign_type = str(payload.get('campaign_type') or 'operational').strip().lower()
    if campaign_type not in dict(OrganizationEmailCampaign.TYPE_CHOICES):
        raise ValidationError({'campaign_type': 'Choose governance, operational, or marketing.'})
    if campaign_type == 'marketing' and not TIER_LIMITS[subscription.tier]['campaigns']:
        raise ValidationError({'subscription': 'Marketing campaigns require the Enterprise email tier.'})
    if subscription.status != 'active':
        raise ValidationError({'subscription': 'Email service is not active for this organization.'})

    recipients = _validate_recipients(payload.get('recipients'))
    if len(recipients) > _remaining_sends(organization):
        raise ValidationError({'recipients': 'This send would exceed the monthly email volume limit.'})
    consent_confirmed = bool(payload.get('consent_confirmed'))
    if campaign_type == 'marketing' and not consent_confirmed:
        raise ValidationError({'consent_confirmed': 'Confirm recipient consent before sending marketing email.'})

    sender = organization.email_accounts.filter(id=payload.get('sender_id'), is_active=True).first()
    if not sender:
        raise ValidationError({'sender_id': 'Choose an active organization email account.'})
    subject = str(payload.get('subject') or '').strip()
    html_body = str(payload.get('html_body') or '').strip()
    if not subject or not html_body:
        raise ValidationError({'detail': 'subject and html_body are required.'})

    campaign = OrganizationEmailCampaign.objects.create(
        organization=organization,
        sender=sender,
        created_by=actor,
        campaign_type=campaign_type,
        subject=subject[:255],
        html_body=html_body,
        recipients=recipients,
        consent_confirmed=consent_confirmed,
        status='sending',
    )
    deliveries = []
    for recipient in recipients:
        body = html_body
        if campaign_type == 'marketing':
            body = f'{html_body}<hr><p><a href="{escape(_unsubscribe_url(organization, recipient))}">Unsubscribe</a></p>'
        deliveries.append(_send_message(
            sender_address=sender.address,
            recipient=recipient,
            subject=campaign.subject,
            html_body=body,
            organization=organization,
            campaign=campaign,
        ))
    campaign.status = 'sent' if all(delivery.status == 'sent' for delivery in deliveries) else 'failed'
    campaign.sent_at = timezone.now()
    campaign.save(update_fields=['status', 'sent_at', 'updated_at'])
    log_platform_audit_event(
        domain='email', event_type='email.campaign_sent', action='email_campaign_sent',
        actor=actor, organization=organization, resource_type='OrganizationEmailCampaign',
        resource_id=str(campaign.id), resource_name=campaign.subject,
        summary=f'Sent {campaign.campaign_type} email campaign to {len(recipients)} recipients',
        metadata={'campaign_type': campaign.campaign_type, 'recipient_count': len(recipients), 'status': campaign.status},
    )
    return campaign, deliveries


def send_system_notification(*, recipient, subject, title, message, event_type, organization=None):
    if not recipient:
        return None
    html_body = (
        f'<h1>{escape(title)}</h1><p>{escape(message)}</p>'
        '<p>This is an automated AtonixCorp service notification.</p>'
    )
    return _send_message(
        sender_address=getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@atonixcorp.local'),
        recipient=recipient,
        subject=subject,
        html_body=html_body,
        organization=organization,
        event_type=event_type,
    )
