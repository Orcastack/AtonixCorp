"""Email verification tokens and minimal plain-text delivery."""
from __future__ import annotations

import hashlib
import secrets
from datetime import timedelta
from urllib.parse import urlencode

from django.conf import settings
from django.core.mail import send_mail
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
    """Replace outstanding tokens and send one short plain-text verification email."""
    token = secrets.token_urlsafe(32)
    expires_at = timezone.now() + timedelta(seconds=settings.EMAIL_VERIFICATION_TOKEN_TTL_SECONDS)
    EmailVerificationToken.objects.filter(user=user, used_at__isnull=True).delete()
    EmailVerificationToken.objects.create(user=user, token_hash=_token_hash(token), expires_at=expires_at)
    support_email = settings.EMAIL_SUPPORT_EMAIL
    body = (
        f'Hello {user.get_full_name() or user.username},\n\n'
        'Verify your AtonixCorp account to continue.\n\n'
        f'{_verification_url(token)}\n\n'
        f'This secure link expires in {settings.EMAIL_VERIFICATION_TOKEN_TTL_SECONDS // 60} minutes and can be used once. '
        'If you did not create this account, you can ignore this email.\n\n'
        f'Support: {support_email}\n'
        'This message is for account verification only; do not forward the link.'
    )
    send_mail('Verify Your Account', body, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False)


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