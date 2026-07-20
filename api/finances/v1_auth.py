"""
AtonixCorp API v1 – Authentication helpers
============================================
Supports two credential flows:

1. OAuth 2.0 client_credentials grant
   POST /v1/auth/token  →  { access_token, token_type, expires_in }

2. API Key Bearer authentication
   Authorization: Bearer <raw_token>

The raw bearer token is never stored; only its SHA-256 digest is kept in
APIKey.token_hash.  Multi-tenant isolation is enforced by binding every
token to a single Organization.
"""
import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from .models import APIKey, OAuthApplication

# Token TTL in seconds (1 hour, matching the directive spec)
TOKEN_TTL_SECONDS = 3600
CLI_API_KEY_DELIMITER = '.'


def current_api_environment() -> str:
    return getattr(
        settings,
        'ATONIXCORP_API_ENVIRONMENT',
        getattr(settings, 'ATONIXCORP_API_ENVIRONMENT', 'sandbox' if settings.DEBUG else 'production'),
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def compose_cli_api_key(client_id: str, client_secret: str) -> str:
    return f"{client_id}{CLI_API_KEY_DELIMITER}{client_secret}"


def parse_cli_api_key(api_key: str) -> tuple[str, str]:
    raw_value = (api_key or '').strip()
    if not raw_value or CLI_API_KEY_DELIMITER not in raw_value:
        raise AuthenticationFailed('The provided API key is invalid or expired.')

    client_id, client_secret = raw_value.split(CLI_API_KEY_DELIMITER, 1)
    if not client_id or not client_secret:
        raise AuthenticationFailed('The provided API key is invalid or expired.')
    return client_id, client_secret


def issue_access_token(application: OAuthApplication, *, source: str = 'oauth_client_credentials') -> dict:
    """
    Create and persist a new APIKey for the given OAuth application.
    Returns a dict suitable for the /v1/auth/token response body.
    """
    raw_token = secrets.token_hex(32)           # 64-char hex string
    token_hash = _sha256(raw_token)
    token_prefix = raw_token[:8]
    expires_at = timezone.now() + timedelta(seconds=TOKEN_TTL_SECONDS)

    APIKey.objects.create(
        organization=application.organization,
        application=application,
        token_hash=token_hash,
        token_prefix=token_prefix,
        scopes=application.scopes,
        environment=application.environment,
        source_metadata={'source': source},
        expires_at=expires_at,
        created_by=application.created_by,
    )

    return {
        "access_token": raw_token,
        "token_type": "Bearer",
        "expires_in": TOKEN_TTL_SECONDS,
    }


def validate_client_credentials(client_id: str, client_secret: str):
    """
    Validate client_id / client_secret against OAuthApplication.
    Returns the OAuthApplication instance or raises AuthenticationFailed.
    """
    try:
        app = OAuthApplication.objects.select_related('organization').get(
            client_id=client_id,
            is_active=True,
        )
    except OAuthApplication.DoesNotExist:
        raise AuthenticationFailed("Invalid client credentials.")

    if app.client_secret_hash != _sha256(client_secret):
        raise AuthenticationFailed("Invalid client credentials.")

    if app.environment != current_api_environment():
        raise AuthenticationFailed("Client credentials are not valid for this environment.")

    return app


def validate_cli_api_key(api_key: str):
    client_id, client_secret = parse_cli_api_key(api_key)
    return validate_client_credentials(client_id, client_secret)


# ---------------------------------------------------------------------------
# DRF Authentication backend
# ---------------------------------------------------------------------------

class APIKeyAuthentication(BaseAuthentication):
    """
    Authenticate requests that carry an API key issued via the
    client_credentials grant.

    Header format:
        Authorization: Bearer <raw_token>

    Falls through (returns None) when the header is absent or the token is
    not found in the APIKey table, allowing SimpleJWT to handle ordinary
    user sessions.
    """

    def authenticate(self, request):
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if not auth_header.startswith("Bearer "):
            return None

        raw_token = auth_header[7:].strip()
        if not raw_token:
            return None

        token_hash = _sha256(raw_token)

        try:
            api_key = APIKey.objects.select_related(
                "organization", "application__created_by"
            ).get(token_hash=token_hash, is_revoked=False)
        except APIKey.DoesNotExist:
            # Not an API key – let JWT auth take over
            return None

        if api_key.expires_at <= timezone.now():
            raise AuthenticationFailed("Access token has expired.")

        if api_key.environment != current_api_environment():
            raise AuthenticationFailed("Access token is not valid for this environment.")

        # Non-blocking last-used timestamp update
        APIKey.objects.filter(pk=api_key.pk).update(last_used_at=timezone.now())

        # Attach the resolved organization so views can read it directly
        request._v1_organization = api_key.organization

        # Use the application owner when available, otherwise fall back to
        # the organization owner so DRF permission checks still work.
        user = api_key.application.created_by or api_key.organization.owner
        return (user, api_key)

    def authenticate_header(self, request):
        return 'Bearer realm="AtonixCorp API v1"'
