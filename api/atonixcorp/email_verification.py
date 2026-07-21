"""Email verification tokens and branded transactional delivery."""
from __future__ import annotations

import hashlib
import secrets
from datetime import timedelta
from urllib.parse import urlencode

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .email_template_service import send_templated_email
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
    send_templated_email(
        template_name='verification',
        subject='Confirm your email for AtonixCorp',
        recipient=user.email,
        context={
            'user_name': user_name,
            'verification_link': verification_url,
            'expiration_minutes': expiration_minutes,
        },
    )


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