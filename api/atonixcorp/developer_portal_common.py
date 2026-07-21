import time

from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed, NotAuthenticated, PermissionDenied, Throttled, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView


def developer_error_code_from_status(status_code):
    return {
        400: 'INVALID_REQUEST',
        401: 'UNAUTHORIZED',
        403: 'FORBIDDEN',
        404: 'NOT_FOUND',
        405: 'METHOD_NOT_ALLOWED',
        409: 'CONFLICT',
        429: 'RATE_LIMIT_EXCEEDED',
    }.get(status_code, 'INTERNAL_ERROR')


def developer_standard_error_payload(*, code, message, details=None):
    return {
        'error': {
            'code': code,
            'message': message,
            'details': details or {},
        }
    }


def developer_standard_error_response(*, code, message, details=None, status_code=status.HTTP_400_BAD_REQUEST):
    return Response(
        developer_standard_error_payload(code=code, message=message, details=details),
        status=status_code,
    )


def _extract_client_ip(request):
    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def _log_developer_portal_request(request, response):
    resolver_match = getattr(request, 'resolver_match', None)
    if resolver_match is None:
        return

    tracked_view_names = {
        'developer-api-list',
        'developer-api-detail',
        'developer-api-endpoints',
        'developer-api-endpoint-detail',
        'developer-search',
        'developer-docs-authentication',
        'developer-docs-errors',
        'developer-status',
        'developer-key-request',
        'public-api-list',
        'public-api-detail',
        'public-api-endpoints',
        'public-api-endpoint-detail',
        'public-api-search',
        'public-api-docs',
        'public-api-docs-detail',
        'public-key-register',
        'public-status',
    }
    if resolver_match.view_name not in tracked_view_names:
        return

    try:
        from django.utils import timezone
        from .models import DeveloperAPI, DeveloperAPIEndpoint, DeveloperPortalAPILog, DeveloperPortalKeyRequest, RateLimitProfile

        slug = resolver_match.kwargs.get('slug')
        endpoint_id = resolver_match.kwargs.get('endpoint_id')

        api_service = DeveloperAPI.objects.filter(slug=slug).first() if slug else None
        endpoint = DeveloperAPIEndpoint.objects.filter(id=endpoint_id).first() if endpoint_id else None

        response_data = getattr(response, 'data', None)
        request_record = None
        if isinstance(response_data, dict) and response_data.get('request_id'):
            request_record = DeveloperPortalKeyRequest.objects.filter(pk=response_data['request_id']).first()

        rate_limit_profile = None
        if request_record is not None and request_record.rate_limit_profile_id:
            rate_limit_profile = request_record.rate_limit_profile
        elif api_service is not None and api_service.rate_limit_profile_id:
            rate_limit_profile = api_service.rate_limit_profile
        else:
            rate_limit_profile = RateLimitProfile.objects.filter(is_default=True).order_by('id').first()

        started_at = getattr(request, '_developer_portal_started_at', None)
        response_time_ms = max(int((time.monotonic() - started_at) * 1000), 0) if started_at is not None else 0
        DeveloperPortalAPILog.objects.create(
            api_service=api_service,
            endpoint=endpoint,
            key_request=request_record,
            rate_limit_profile=rate_limit_profile,
            method=request.method,
            path=request.path,
            status_code=getattr(response, 'status_code', 200),
            request_timestamp=timezone.now(),
            response_time_ms=response_time_ms,
            client_ip=_extract_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            source_metadata={
                'view_name': resolver_match.view_name,
                'route_kwargs': resolver_match.kwargs,
            },
        )
    except Exception:
        return


def normalize_developer_error_response_data(data, status_code):
    if isinstance(data, dict) and 'error' in data:
        return data

    if isinstance(data, dict) and 'detail' in data:
        detail = data.get('detail')
        detail_code = getattr(detail, 'code', None)
        code = {
            'throttled': 'RATE_LIMIT_EXCEEDED',
            'authentication_failed': 'UNAUTHORIZED',
            'not_authenticated': 'UNAUTHORIZED',
            'permission_denied': 'FORBIDDEN',
            'not_found': 'NOT_FOUND',
        }.get(detail_code, developer_error_code_from_status(status_code))
        details = {key: value for key, value in data.items() if key != 'detail'}
        return developer_standard_error_payload(code=code, message=str(detail), details=details)

    if isinstance(data, dict):
        message = 'Request failed.'
        if 'non_field_errors' in data and data['non_field_errors']:
            message = str(data['non_field_errors'][0])
        elif data:
            first_key = next(iter(data))
            first_value = data[first_key]
            if isinstance(first_value, list) and first_value:
                message = f'{first_key}: {first_value[0]}'
            else:
                message = f'{first_key}: {first_value}'
        return developer_standard_error_payload(
            code=developer_error_code_from_status(status_code),
            message=message,
            details=data,
        )

    return developer_standard_error_payload(
        code=developer_error_code_from_status(status_code),
        message=str(data),
        details={},
    )


class DeveloperFacingAPIView(APIView):
    def initial(self, request, *args, **kwargs):
        request._developer_portal_started_at = time.monotonic()
        return super().initial(request, *args, **kwargs)

    def handle_exception(self, exc):
        if isinstance(exc, ValueError):
            return developer_standard_error_response(
                code='INVALID_REQUEST',
                message=str(exc),
                details={},
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        if isinstance(exc, (AuthenticationFailed, NotAuthenticated, PermissionDenied, Throttled, ValidationError)):
            response = super().handle_exception(exc)
            if response is not None:
                response.data = normalize_developer_error_response_data(response.data, response.status_code)
            return response
        return super().handle_exception(exc)

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        if getattr(response, 'status_code', 200) >= 400 and hasattr(response, 'data'):
            response.data = normalize_developer_error_response_data(response.data, response.status_code)
            response._is_rendered = False
        _log_developer_portal_request(request, response)
        return response


class StandardizedTokenObtainPairView(DeveloperFacingAPIView, TokenObtainPairView):
    pass


class StandardizedTokenRefreshView(DeveloperFacingAPIView, TokenRefreshView):
    pass