from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.response import Response

from .models import Organization, TeamMember
from .v1_auth import issue_access_token, validate_cli_api_key
from .v1_views import (
    V1BaseAPIView,
    V1PublicAPIView,
    _audit,
    _organization_from_request,
    _parse_public_id,
    _public_id,
    _source_metadata,
    _standard_error_payload,
)


def _cli_role_for_user(organization, user):
    membership = TeamMember.objects.select_related('role').filter(
        organization=organization,
        user=user,
        is_active=True,
    ).first()
    if membership and membership.role:
        return (membership.role.code or membership.role.name or 'developer').lower()
    if organization.owner_id == getattr(user, 'id', None):
        return 'org_owner'
    return 'developer'


def _cli_user_payload(organization, user):
    return {
        'id': _public_id('user', user.pk),
        'email': user.email or user.username,
        'role': _cli_role_for_user(organization, user),
    }


def _cli_login_success_payload(application, token_payload):
    organization = application.organization
    user = application.created_by or organization.owner
    return {
        'access_token': token_payload['access_token'],
        'expires_in': token_payload['expires_in'],
        'organization_id': _public_id('org', organization.pk),
        'user': _cli_user_payload(organization, user),
    }


class CLIAuthLoginView(V1PublicAPIView):
    def post(self, request):
        payload = request.data or {}
        api_key = (payload.get('api_key') or '').strip()
        organization_id = (payload.get('organization_id') or '').strip()

        if not api_key or not organization_id:
            return Response(
                _standard_error_payload(
                    code='INVALID_REQUEST',
                    message='Missing required flags. Use --api-key and --org.',
                    details={},
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            organization_pk = _parse_public_id(organization_id, 'org')
        except (TypeError, ValueError):
            return Response(
                _standard_error_payload(
                    code='INVALID_REQUEST',
                    message='organization_id must be a valid AtonixCorp organization identifier.',
                    details={},
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )

        organization = Organization.objects.filter(pk=organization_pk).first()
        if organization is None:
            return Response(
                _standard_error_payload(
                    code='ORG_NOT_FOUND',
                    message='The requested organization was not found.',
                    details={},
                ),
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            application = validate_cli_api_key(api_key)
        except AuthenticationFailed:
            return Response(
                _standard_error_payload(
                    code='INVALID_API_KEY',
                    message='The provided API key is invalid or expired.',
                    details={},
                ),
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if application.organization_id != organization.pk:
            return Response(
                _standard_error_payload(
                    code='INVALID_API_KEY',
                    message='The provided API key is invalid or expired.',
                    details={},
                ),
                status=status.HTTP_401_UNAUTHORIZED,
            )

        token_payload = issue_access_token(application, source='cli_login')
        user = application.created_by or organization.owner
        _audit(
            organization,
            user,
            'create',
            'CLIAuthSession',
            application.pk,
            {'flow': 'cli-login', **_source_metadata(request)},
            ip_address=request.META.get('REMOTE_ADDR'),
        )
        return Response(_cli_login_success_payload(application, token_payload), status=status.HTTP_200_OK)


class CLIAuthRefreshView(V1PublicAPIView):
    def post(self, request):
        payload = request.data or {}
        api_key = (payload.get('api_key') or '').strip()
        if not api_key:
            return Response(
                _standard_error_payload(
                    code='INVALID_REQUEST',
                    message='api_key is required.',
                    details={},
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            application = validate_cli_api_key(api_key)
        except AuthenticationFailed:
            return Response(
                _standard_error_payload(
                    code='INVALID_API_KEY',
                    message='The provided API key is invalid or expired.',
                    details={},
                ),
                status=status.HTTP_401_UNAUTHORIZED,
            )

        token_payload = issue_access_token(application, source='cli_refresh')
        organization = application.organization
        user = application.created_by or organization.owner
        _audit(
            organization,
            user,
            'update',
            'CLIAuthSession',
            application.pk,
            {'flow': 'cli-refresh', **_source_metadata(request)},
            ip_address=request.META.get('REMOTE_ADDR'),
        )
        return Response(_cli_login_success_payload(application, token_payload), status=status.HTTP_200_OK)


class CLIAuthMeView(V1BaseAPIView):
    def get(self, request):
        organization = _organization_from_request(request, required=True)
        auth = getattr(request, 'auth', None)
        expires_at = getattr(auth, 'expires_at', None)
        return Response(
            {
                'organization': {
                    'id': _public_id('org', organization.pk),
                    'name': organization.name,
                },
                'user': _cli_user_payload(organization, request.user),
                'session': {
                    'expires_at': expires_at.isoformat() if expires_at else None,
                    'token_type': 'Bearer',
                },
            },
            status=status.HTTP_200_OK,
        )