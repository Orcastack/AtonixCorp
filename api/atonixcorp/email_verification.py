"""Email verification tokens and branded transactional delivery."""
from __future__ import annotations

import hashlib
import secrets
from datetime import timedelta
from html import escape
from urllib.parse import urlencode

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import EmailVerificationToken, UserProfile


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


def _verification_url(token: str) -> str:
    base_url = settings.FRONTEND_BASE_URL.rstrip('/')
    return f'{base_url}/verify-email?{urlencode({"token": token})}'


def send_verification_email(user) -> None:
    """Replace outstanding tokens and deliver a single-use verification message."""
    token = secrets.token_urlsafe(32)
    expires_at = timezone.now() + timedelta(seconds=settings.EMAIL_VERIFICATION_TOKEN_TTL_SECONDS)
    EmailVerificationToken.objects.filter(user=user, used_at__isnull=True).delete()
    EmailVerificationToken.objects.create(user=user, token_hash=_token_hash(token), expires_at=expires_at)
    user_name = user.get_full_name().strip() or user.username
    verification_url = _verification_url(token)
    expiration_minutes = settings.EMAIL_VERIFICATION_TOKEN_TTL_SECONDS // 60
    support_email = getattr(settings, 'EMAIL_SUPPORT_EMAIL', 'support@atonixcorp.com')
    body = (
        f'Hi {user_name},\n\n'
        'Thanks for joining AtonixCorp. Before you continue, we need to confirm your email address.\n\n'
        f'Verify your account: {verification_url}\n\n'
        f'For your security, this link expires in {expiration_minutes} minutes and can only be used once. '
        'If this was not you, no action is required.\n\n'
        'The AtonixCorp Security Team\n'
        f'{support_email}\n'
    )
    html_body = f'''<!doctype html>
<html lang="en">
    <body style="margin:0;padding:0;background:#f4f7fb;color:#172033;font-family:Arial,sans-serif;">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="padding:32px 16px;background:#f4f7fb;">
            <tr><td align="center">
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:600px;background:#ffffff;border:1px solid #dce3ed;">
                    <tr><td style="padding:28px 36px;background:#0b1f3b;color:#ffffff;">
                        <strong style="font-size:20px;letter-spacing:0;">AtonixCorp</strong>
                        <span style="display:block;margin-top:6px;font-size:12px;letter-spacing:1.2px;text-transform:uppercase;color:#b8d8ef;">Security verification</span>
                    </td></tr>
                    <tr><td style="padding:36px;">
                        <h1 style="margin:0 0 18px;font-size:26px;line-height:1.25;color:#0b1f3b;">Confirm your email address</h1>
                        <p style="margin:0 0 16px;font-size:16px;line-height:1.6;">Hi {escape(user_name)},</p>
                        <p style="margin:0 0 24px;font-size:16px;line-height:1.6;">Thanks for joining AtonixCorp. Before you continue, we need to confirm your email address.</p>
                        <table role="presentation" cellspacing="0" cellpadding="0"><tr><td style="background:#007f99;">
                            <a href="{escape(verification_url, quote=True)}" style="display:inline-block;padding:14px 22px;color:#ffffff;font-size:16px;font-weight:bold;text-decoration:none;">Verify your account</a>
                        </td></tr></table>
                        <p style="margin:28px 0 0;font-size:14px;line-height:1.6;color:#526176;">For your security, this link expires in {expiration_minutes} minutes and can only be used once. If this was not you, no action is required.</p>
                        <p style="margin:24px 0 0;font-size:14px;line-height:1.6;color:#526176;">The AtonixCorp Security Team<br><a href="mailto:{escape(support_email, quote=True)}" style="color:#007f99;">{escape(support_email)}</a></p>
                    </td></tr>
                    <tr><td style="padding:20px 36px;border-top:1px solid #dce3ed;font-size:12px;line-height:1.5;color:#68778d;">This is an account-security message. Do not forward your verification link.</td></tr>
                </table>
            </td></tr>
        </table>
    </body>
</html>'''
    message = EmailMultiAlternatives(
        subject='Confirm your email for AtonixCorp',
        body=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email],
    )
    message.attach_alternative(html_body, 'text/html')
    message.send(fail_silently=False)


@transaction.atomic
def verify_email_token(raw_token: str):
    token_hash = _token_hash(str(raw_token or ''))
    token = EmailVerificationToken.objects.select_for_update().select_related('user').filter(
        token_hash=token_hash,
        used_at__isnull=True,
    ).first()
    if token is None or token.expires_at <= timezone.now():
        raise ValidationError({'token': 'This verification link is invalid or has expired.'})

    profile, _ = UserProfile.objects.get_or_create(user=token.user)
    profile.email_verified = True
    profile.email_verified_at = timezone.now()
    profile.save(update_fields=['email_verified', 'email_verified_at', 'updated_at'])
    token.used_at = timezone.now()
    token.save(update_fields=['used_at'])
    return token.user