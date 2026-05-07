import hashlib
import secrets
import time

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Prefetch
from django.utils import timezone
from django.utils.text import slugify
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .developer_portal_common import DeveloperFacingAPIView, developer_standard_error_response
from .models import (
    DeveloperAPI,
    DeveloperAPICategory,
    DeveloperAPIEndpoint,
    DeveloperAPIVersion,
    DeveloperPortalKeyRequest,
    OAuthApplication,
    Organization,
    RateLimitProfile,
    UserProfile,
)
from .platform_views import _database_health
from .v1_auth import compose_cli_api_key


User = get_user_model()
DEVELOPER_PORTAL_START_TIME = time.monotonic()


def _developer_source_metadata(request, extra=None):
    metadata = {
        'source': 'developer_portal',
        'path': request.path,
    }
    remote_addr = request.META.get('REMOTE_ADDR')
    if remote_addr:
        metadata['ip_address'] = remote_addr
    if extra:
        metadata.update(extra)
    return metadata


def _developer_api_version(version):
    return {
        'version': version.version,
        'base_path': version.base_path,
        'summary': version.summary,
        'status': version.status,
        'is_default': version.is_default,
        'release_notes': version.release_notes,
    }


def _developer_api_summary(api):
    default_version = next((version for version in api.versions.all() if version.is_default), None)
    if default_version is None and api.versions.all():
        default_version = api.versions.all()[0]
    return {
        'id': api.pk,
        'slug': api.slug,
        'name': api.name,
        'description': api.description,
        'status': api.status,
        'access_level': api.access_level,
        'auth_type': api.auth_type,
        'data_types': api.data_types,
        'categories': [{'name': category.name, 'slug': category.slug} for category in api.categories.all()],
        'tags': [{'name': tag.name, 'slug': tag.slug} for tag in api.tags.all()],
        'version': default_version.version if default_version else None,
        'is_featured': api.is_featured,
        'rate_limit_profile': {
            'name': api.rate_limit_profile.name,
            'requests_per_minute': api.rate_limit_profile.requests_per_minute,
            'requests_per_day': api.rate_limit_profile.requests_per_day,
        } if api.rate_limit_profile_id else None,
    }


def _developer_endpoint_payload(endpoint):
    return {
        'name': endpoint.name,
        'method': endpoint.method,
        'path': endpoint.path,
        'summary': endpoint.summary,
        'description': endpoint.description,
        'path_parameters': endpoint.path_params,
        'query_parameters': endpoint.query_params,
        'headers': endpoint.headers,
        'scopes': endpoint.scopes,
        'request_example': endpoint.request_example,
        'response_example': endpoint.response_example,
        'error_responses': endpoint.error_responses,
    }


def _developer_api_detail(api):
    versions = list(api.versions.all())
    default_version = next((version for version in versions if version.is_default), None)
    if default_version is None and versions:
        default_version = versions[0]

    return {
        **_developer_api_summary(api),
        'overview': api.overview,
        'use_cases': api.use_cases,
        'data_domains': api.data_domains,
        'rate_limits': api.rate_limits,
        'compliance_notes': api.compliance_notes,
        'keywords': api.keywords,
        'versions': [_developer_api_version(version) for version in versions],
        'default_version': _developer_api_version(default_version) if default_version else None,
        'endpoints': [_developer_endpoint_payload(endpoint) for endpoint in default_version.endpoints.all()] if default_version else [],
    }


def _developer_endpoint_detail(api, endpoint):
    return {
        'api': {
            'slug': api.slug,
            'name': api.name,
            'version': next((version.version for version in api.versions.all() if version.is_default), None),
        },
        'endpoint': {
            'id': endpoint.id,
            **_developer_endpoint_payload(endpoint),
        },
    }


def _developer_catalog_queryset():
    endpoint_prefetch = Prefetch('endpoints', queryset=DeveloperAPIEndpoint.objects.order_by('display_order', 'method', 'path'))
    version_prefetch = Prefetch('versions', queryset=DeveloperAPIVersion.objects.order_by('-is_default', 'version').prefetch_related(endpoint_prefetch))
    return DeveloperAPI.objects.prefetch_related('categories', 'tags', version_prefetch).order_by('featured_rank', 'name')


def _developer_matches_query(api, query):
    if not query:
        return True
    normalized_query = query.lower()
    haystacks = [
        api.name,
        api.description,
        api.overview,
        ' '.join(api.data_domains or []),
        ' '.join(api.data_types or []),
        ' '.join(api.keywords or []),
        ' '.join(category.name for category in api.categories.all()),
        ' '.join(tag.name for tag in api.tags.all()),
    ]
    for version in api.versions.all():
        haystacks.extend([
            version.version,
            version.base_path,
            version.summary,
            version.release_notes,
        ])
        for endpoint in version.endpoints.all():
            haystacks.extend([
                endpoint.name,
                endpoint.method,
                endpoint.path,
                endpoint.summary,
                endpoint.description,
                ' '.join(endpoint.keywords or []),
            ])
    return normalized_query in ' '.join(filter(None, haystacks)).lower()


def _filter_catalog(queryset, *, query=None, category=None, status=None, data_type=None, access_level=None):
    items = []
    for api in queryset:
        category_slugs = {item.slug for item in api.categories.all()}
        data_types = set(api.data_types or [])
        if category and category not in category_slugs:
            continue
        if status and api.status != status:
            continue
        if access_level and api.access_level != access_level:
            continue
        if data_type and data_type not in data_types:
            continue
        if not _developer_matches_query(api, query):
            continue
        items.append(api)
    return items


def _paginate(items, *, page, page_size):
    total = len(items)
    total_pages = max((total + page_size - 1) // page_size, 1)
    current_page = min(max(page, 1), total_pages)
    start = (current_page - 1) * page_size
    end = start + page_size
    return {
        'results': items[start:end],
        'pagination': {
            'page': current_page,
            'pageSize': page_size,
            'total': total,
            'totalPages': total_pages,
        },
    }


class DeveloperAPIListView(DeveloperFacingAPIView):
    permission_classes = [AllowAny]

    def get(self, request):
        page = int(request.query_params.get('page') or 1)
        page_size = min(max(int(request.query_params.get('pageSize') or 10), 1), 50)
        items = _filter_catalog(
            _developer_catalog_queryset(),
            query=(request.query_params.get('q') or '').strip(),
            category=(request.query_params.get('category') or '').strip(),
            status=(request.query_params.get('status') or '').strip(),
            data_type=(request.query_params.get('type') or '').strip(),
            access_level=(request.query_params.get('accessLevel') or '').strip(),
        )
        paginated = _paginate(items, page=page, page_size=page_size)
        return Response(
            {
                'results': [_developer_api_summary(api) for api in paginated['results']],
                'pagination': paginated['pagination'],
                'available_filters': {
                    'categories': [
                        {'name': category.name, 'slug': category.slug}
                        for category in DeveloperAPICategory.objects.order_by('display_order', 'name')
                    ],
                    'statuses': ['stable', 'beta', 'deprecated'],
                    'types': ['real-time', 'end-of-day', 'historical', 'metadata'],
                    'access_levels': ['public', 'partner', 'internal'],
                },
            }
        )


class DeveloperSearchView(DeveloperFacingAPIView):
    permission_classes = [AllowAny]

    def get(self, request):
        page = int(request.query_params.get('page') or 1)
        page_size = min(max(int(request.query_params.get('pageSize') or 10), 1), 50)
        query = (request.query_params.get('q') or '').strip()
        if not query:
            return developer_standard_error_response(
                code='INVALID_REQUEST',
                message='q is required.',
                details={'field': 'q'},
            )
        items = _filter_catalog(
            _developer_catalog_queryset(),
            query=query,
            category=(request.query_params.get('category') or '').strip(),
            status=(request.query_params.get('status') or '').strip(),
            data_type=(request.query_params.get('type') or '').strip(),
            access_level=(request.query_params.get('accessLevel') or '').strip(),
        )
        paginated = _paginate(items, page=page, page_size=page_size)
        return Response(
            {
                'query': query,
                'results': [_developer_api_summary(api) for api in paginated['results']],
                'pagination': paginated['pagination'],
            }
        )


class DeveloperAPIDetailView(DeveloperFacingAPIView):
    permission_classes = [AllowAny]

    def get(self, request, slug):
        api = _developer_catalog_queryset().filter(slug=slug).first()
        if api is None:
            return developer_standard_error_response(
                code='NOT_FOUND',
                message='The requested API catalog entry was not found.',
                details={'slug': slug},
                status_code=404,
            )
        return Response(_developer_api_detail(api))


class DeveloperAPIEndpointListView(DeveloperFacingAPIView):
    permission_classes = [AllowAny]

    def get(self, request, slug):
        api = _developer_catalog_queryset().filter(slug=slug).first()
        if api is None:
            return developer_standard_error_response(
                code='NOT_FOUND',
                message='The requested API catalog entry was not found.',
                details={'slug': slug},
                status_code=404,
            )

        endpoints = []
        for version in api.versions.all():
            for endpoint in version.endpoints.all():
                endpoints.append(
                    {
                        'id': endpoint.id,
                        'version': version.version,
                        **_developer_endpoint_payload(endpoint),
                    }
                )

        return Response(
            {
                'api': {
                    'slug': api.slug,
                    'name': api.name,
                    'status': api.status,
                    'version': next((version.version for version in api.versions.all() if version.is_default), None),
                },
                'endpoints': endpoints,
            }
        )


class DeveloperAPIEndpointDetailView(DeveloperFacingAPIView):
    permission_classes = [AllowAny]

    def get(self, request, slug, endpoint_id):
        api = _developer_catalog_queryset().filter(slug=slug).first()
        if api is None:
            return developer_standard_error_response(
                code='NOT_FOUND',
                message='The requested API catalog entry was not found.',
                details={'slug': slug},
                status_code=404,
            )

        endpoint = next(
            (
                endpoint_item
                for version in api.versions.all()
                for endpoint_item in version.endpoints.all()
                if endpoint_item.id == endpoint_id
            ),
            None,
        )
        if endpoint is None:
            return developer_standard_error_response(
                code='NOT_FOUND',
                message='The requested API endpoint was not found.',
                details={'slug': slug, 'endpoint_id': endpoint_id},
                status_code=404,
            )

        return Response(_developer_endpoint_detail(api, endpoint))


class DeveloperAuthenticationDocsView(DeveloperFacingAPIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response(
            {
                'slug': 'authentication',
                'title': 'Authentication',
                'summary': 'Ledgora supports OAuth 2.0 client credentials for server-to-server access and API-key based CLI login for developer workflows.',
                'supported_methods': [
                    {
                        'type': 'oauth2_client_credentials',
                        'token_endpoint': '/v1/auth/token',
                        'headers': ['Authorization: Bearer <token>', 'X-Organization-Id: org_<id>'],
                        'example': 'curl -X POST "https://api.ledgora.com/v1/auth/token" -H "Content-Type: application/json" -d "{\"client_id\":\"...\",\"client_secret\":\"...\",\"grant_type\":\"client_credentials\"}"',
                    },
                    {
                        'type': 'developer_cli_api_key',
                        'token_endpoint': '/auth/cli-login',
                        'headers': ['Authorization: Bearer <token>', 'X-Organization-Id: org_<id>'],
                        'example': 'curl -X POST "https://api.ledgora.com/auth/cli-login" -H "Content-Type: application/json" -d "{\"api_key\":\"client_id.client_secret\",\"organization_id\":\"org_123\"}"',
                    },
                ],
                'error_handling': {
                    '401': 'Credentials are missing, invalid, or expired.',
                    '403': 'The authenticated principal does not have the required organization or scope access.',
                },
            }
        )


class DeveloperErrorsDocsView(DeveloperFacingAPIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response(
            {
                'slug': 'errors',
                'title': 'Errors & Conventions',
                'summary': 'Developer-facing backend endpoints return a standard error envelope.',
                'error_format': {
                    'error': {
                        'code': 'RATE_LIMIT_EXCEEDED',
                        'message': 'You have exceeded your rate limit.',
                        'details': {'limit': 1000, 'window': '1 minute'},
                    }
                },
                'http_statuses': [
                    {'status': 400, 'meaning': 'Validation or request-shape failure.'},
                    {'status': 401, 'meaning': 'Authentication failed or credentials are missing.'},
                    {'status': 403, 'meaning': 'Authenticated but not authorized for the requested scope or resource.'},
                    {'status': 404, 'meaning': 'Requested resource was not found.'},
                    {'status': 429, 'meaning': 'Rate limit exceeded. Apply backoff and retry later.'},
                    {'status': 500, 'meaning': 'Unexpected server-side failure.'},
                ],
                'retry_guidance': 'Use idempotency keys for write operations and exponential backoff when retrying 429 and eligible 5xx responses.',
            }
        )


class DeveloperStatusView(DeveloperFacingAPIView):
    permission_classes = [AllowAny]

    def get(self, request):
        database_status = _database_health()
        overall_status = 'operational' if database_status == 'ok' else 'degraded'
        uptime_seconds = max(int(time.monotonic() - DEVELOPER_PORTAL_START_TIME), 0)
        return Response(
            {
                'status': overall_status,
                'service': 'developer-portal',
                'version': settings.APP_VERSION,
                'uptime_seconds': uptime_seconds,
                'updated_at': timezone.now().isoformat(),
                'components': [
                    {'name': 'catalog', 'status': 'operational'},
                    {'name': 'search', 'status': 'operational'},
                    {'name': 'api_key_issuance', 'status': 'operational'},
                    {'name': 'database', 'status': 'operational' if database_status == 'ok' else 'degraded'},
                ],
            }
        )


class DeveloperKeyRequestView(DeveloperFacingAPIView):
    permission_classes = [AllowAny]

    @transaction.atomic
    def post(self, request):
        payload = request.data or {}
        full_name = (payload.get('name') or '').strip()
        first_name = (payload.get('first_name') or '').strip()
        last_name = (payload.get('last_name') or '').strip()
        if full_name and not first_name and not last_name:
            name_parts = full_name.split()
            first_name = name_parts[0]
            last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else 'Developer'
        email = (payload.get('email') or '').strip().lower()
        organization_name = (payload.get('organization') or '').strip()
        intended_use = (payload.get('intended_use') or '').strip()

        missing = [field for field, value in {
            'first_name': first_name,
            'last_name': last_name,
            'email': email,
        }.items() if not value]
        if missing:
            return developer_standard_error_response(
                code='INVALID_REQUEST',
                message=f'Missing required field(s): {", ".join(missing)}.',
                details={'missing_fields': missing},
            )

        user = User.objects.filter(email=email).first()
        created_user = False
        if user is None:
            base_username = slugify(email.split('@')[0]) or 'developer'
            username = base_username
            counter = 1
            while User.objects.filter(username=username).exists():
                counter += 1
                username = f'{base_username}-{counter}'
            user = User.objects.create(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
            )
            user.set_unusable_password()
            user.save(update_fields=['password'])
            created_user = True
        else:
            updates = []
            if first_name and user.first_name != first_name:
                user.first_name = first_name
                updates.append('first_name')
            if last_name and user.last_name != last_name:
                user.last_name = last_name
                updates.append('last_name')
            if updates:
                user.save(update_fields=updates)

        UserProfile.objects.get_or_create(user=user, defaults={'account_type': 'personal'})

        resolved_organization_name = organization_name or f'{first_name} {last_name} Developer Workspace'
        organization = Organization.objects.filter(owner=user, name=resolved_organization_name).first()
        if organization is None:
            base_slug = slugify(resolved_organization_name) or f'developer-{user.pk}'
            slug = base_slug
            suffix = 1
            while Organization.objects.filter(slug=slug).exists():
                suffix += 1
                slug = f'{base_slug}-{suffix}'
            organization = Organization.objects.create(
                owner=user,
                name=resolved_organization_name,
                slug=slug,
                primary_country='US',
                primary_currency='USD',
                settings={'source': 'developer_portal'},
            )

        request_record = DeveloperPortalKeyRequest.objects.create(
            first_name=first_name,
            last_name=last_name,
            email=email,
            organization_name=organization.name,
            intended_use=intended_use,
            status='submitted',
            user=user,
            organization=organization,
            rate_limit_profile=RateLimitProfile.objects.filter(is_default=True).order_by('id').first(),
            source_metadata=_developer_source_metadata(request, {'created_user': created_user}),
        )

        raw_secret = secrets.token_urlsafe(32)
        client_id = f'dev_{secrets.token_urlsafe(18)}'
        application = OAuthApplication.objects.create(
            organization=organization,
            name=f'Developer Portal Key {timezone.now().strftime("%Y-%m-%d %H:%M:%S")}',
            client_id=client_id,
            client_secret_hash=hashlib.sha256(raw_secret.encode()).hexdigest(),
            scopes=['org:read', 'accounts:read', 'reports:read', 'market.read'],
            environment='sandbox',
            source_metadata={
                'source': 'developer_portal',
                'intended_use': intended_use,
                'request_id': request_record.pk,
            },
            is_active=True,
            created_by=user,
            updated_by=user,
        )

        request_record.application = application
        request_record.status = 'generated'
        request_record.generated_at = timezone.now()
        request_record.save(update_fields=['application', 'status', 'generated_at', 'updated_at'])

        return Response(
            {
                'request_id': request_record.pk,
                'message': 'Developer API key generated. Store this key securely; it will not be shown again.',
                'developer': {
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                },
                'organization': {
                    'id': f'org_{organization.pk}',
                    'name': organization.name,
                },
                'api_key': {
                    'id': f'key_{application.pk}',
                    'client_id': application.client_id,
                    'api_key': compose_cli_api_key(application.client_id, raw_secret),
                    'status': 'ACTIVE',
                    'scopes': application.scopes,
                    'environment': application.environment,
                    'rate_limit_profile': {
                        'name': request_record.rate_limit_profile.name,
                        'requests_per_minute': request_record.rate_limit_profile.requests_per_minute,
                        'requests_per_day': request_record.rate_limit_profile.requests_per_day,
                    } if request_record.rate_limit_profile_id else None,
                },
            },
            status=201,
        )