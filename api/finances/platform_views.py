import json
import logging
import secrets

from django.conf import settings
from django.db import connections, models
from django.db.utils import OperationalError
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .developer_portal_common import developer_standard_error_response
from .models import PlatformAuditEvent
from .platform_foundation import log_platform_audit_event
from .serializers import PlatformAuditEventSerializer


def _database_health():
    try:
        connections['default'].cursor()
        return 'ok'
    except OperationalError:
        return 'error'


def _extract_platform_token(request):
    authorization = request.headers.get('Authorization', '')
    if authorization.startswith('Bearer '):
        return authorization.split(' ', 1)[1].strip()
    return request.headers.get('X-Platform-Token', '').strip()


@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
def health_check(request):
    database_status = _database_health()
    response_status = status.HTTP_200_OK if database_status == 'ok' else status.HTTP_503_SERVICE_UNAVAILABLE
    return Response(
        {
            'status': 'ok' if database_status == 'ok' else 'degraded',
            'service': 'ledgora-backend',
            'environment': settings.DEPLOYMENT_ENVIRONMENT,
            'version': settings.APP_VERSION,
            'timestamp': timezone.now().isoformat(),
            'checks': {
                'database': database_status,
            },
        },
        status=response_status,
    )


@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def ingest_platform_event(request):
    configured_token = settings.PLATFORM_EVENT_TOKEN
    provided_token = _extract_platform_token(request)
    if not configured_token or not secrets.compare_digest(provided_token, configured_token):
        return developer_standard_error_response(
            code='UNAUTHORIZED',
            message='Unauthorized platform event publisher.',
            details={},
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    payload = request.data if isinstance(request.data, dict) else {}
    required_fields = ['event_type', 'source', 'environment', 'status']
    missing_fields = [field for field in required_fields if not payload.get(field)]
    if missing_fields:
        return developer_standard_error_response(
            code='INVALID_REQUEST',
            message=f'Missing required fields: {", ".join(missing_fields)}',
            details={'missing_fields': missing_fields},
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    logger = logging.getLogger(settings.PLATFORM_EVENT_LOGGER)
    logger.info(
        'platform_event %s',
        json.dumps(
            {
                'event_type': payload['event_type'],
                'source': payload['source'],
                'environment': payload['environment'],
                'status': payload['status'],
                'service': payload.get('service', 'unknown'),
                'version': payload.get('version', settings.APP_VERSION),
                'metadata': payload.get('metadata', {}),
                'received_at': timezone.now().isoformat(),
            },
            sort_keys=True,
        ),
    )

    return Response({'accepted': True}, status=status.HTTP_202_ACCEPTED)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def internal_audit_events(request):
    if request.method == 'POST':
        payload = request.data if isinstance(request.data, dict) else {}
        subject_type = payload.get('subject_type')
        subject_id = payload.get('subject_id')
        action = payload.get('action')
        if not all([subject_type, subject_id, action]):
            return Response(
                {'detail': 'subject_type, subject_id, and action are required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        event = log_platform_audit_event(
            domain=payload.get('domain', 'internal'),
            actor=request.user if payload.get('actor_type', 'user') == 'user' else None,
            actor_type=payload.get('actor_type', 'user'),
            actor_id=payload.get('actor_id', str(request.user.id)),
            event_type=payload.get('event_type', action),
            action=action,
            subject_type=subject_type,
            subject_id=subject_id,
            resource_type=payload.get('resource_type', subject_type),
            resource_id=payload.get('resource_id', subject_id),
            resource_name=payload.get('resource_name', ''),
            summary=payload.get('summary', f'{action} {subject_type} {subject_id}'),
            context=payload.get('context', {}),
            diff=payload.get('diff', {}),
            correlation_id=payload.get('correlation_id', ''),
            metadata=payload.get('metadata', {}),
            workspace_id=payload.get('workspace_id'),
        )
        return Response(PlatformAuditEventSerializer(event).data, status=status.HTTP_201_CREATED)

    queryset = PlatformAuditEvent.objects.all().select_related('organization', 'entity', 'actor')
    subject_type = request.query_params.get('subject_type')
    subject_id = request.query_params.get('subject_id')
    actor_id = request.query_params.get('actor_id')
    action = request.query_params.get('action')
    from_value = request.query_params.get('from')
    to_value = request.query_params.get('to')
    correlation_id = request.query_params.get('correlation_id')

    if subject_type:
        queryset = queryset.filter(subject_type=subject_type)
    if subject_id:
        queryset = queryset.filter(subject_id=str(subject_id))
    if actor_id:
        queryset = queryset.filter(models.Q(actor_id=actor_id) | models.Q(actor_identifier=str(actor_id)))
    if action:
        queryset = queryset.filter(action=action)
    if correlation_id:
        queryset = queryset.filter(correlation_id=correlation_id)
    if from_value:
        queryset = queryset.filter(occurred_at__gte=timezone.datetime.fromisoformat(from_value.replace('Z', '+00:00')))
    if to_value:
        queryset = queryset.filter(occurred_at__lte=timezone.datetime.fromisoformat(to_value.replace('Z', '+00:00')))

    serializer = PlatformAuditEventSerializer(queryset[:200], many=True)
    return Response(serializer.data)