import hashlib
import hmac
import json
from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
import secrets
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import F, Q
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.text import slugify
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed, NotAuthenticated, PermissionDenied, Throttled, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .enterprise_views import _accessible_organizations_queryset
from .models import (
    AuditLog,
    BankAccount,
    BankingTransaction,
    Bill,
    BillPayment,
    BookkeepingAccount,
    BookkeepingCategory,
    ChartOfAccounts,
    Customer,
    Entity,
    GeneralLedger,
    IdempotencyKey,
    Invoice,
    InvoiceLineItem,
    JournalEntry,
    MigrationJob,
    OAuthApplication,
    Organization,
    Payment,
    Permission,
    ReconciliationMatch,
    Role,
    SystemEvent,
    TeamMember,
    Transaction,
    Vendor,
    WebhookDelivery,
    WebhookEndpoint,
)
from .v1_auth import compose_cli_api_key, current_api_environment, issue_access_token, validate_client_credentials
from .v1_permissions import APIKeyScopePermission
from .v1_throttles import V1OrganizationBurstThrottle, V1OrganizationEndpointThrottle
from workspaces.models import ParticipantStatus, WorkspaceMember
from workspaces.services import MemberService, PermissionService, WorkspaceService


User = get_user_model()


FINANCIAL_EVENT_SOURCES = {
    'invoices.create': 'invoice.created',
    'invoices.payment': 'invoice.paid',
    'bills.create': 'bill.created',
    'bills.payment': 'bill.paid',
    'journal_entries.post': 'journal_entry.posted',
    'bank_transactions.import': 'bank_transaction.imported',
    'reconciliation.match': 'reconciliation.matched',
}

WEBHOOK_MAX_ATTEMPTS = 3
OPENAPI_SPEC_PATH = Path(__file__).resolve().parent.parent / 'openapi' / 'ledgora-v1-openapi.yaml'


def _sha256(value):
    return hashlib.sha256(value.encode()).hexdigest()


def _public_id(prefix, obj_or_pk):
    pk = getattr(obj_or_pk, 'pk', obj_or_pk)
    return f'{prefix}_{pk}'


def _parse_public_id(raw_value, prefix=None):
    if raw_value in [None, '']:
        return None
    value = str(raw_value).strip()
    if prefix and value.startswith(f'{prefix}_'):
        return int(value.split('_', 1)[1])
    if '_' in value and value.split('_', 1)[1].isdigit():
        return int(value.split('_', 1)[1])
    return int(value)


def _decimal(value, field_name):
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError(f'Invalid decimal value for {field_name}.')


def _date(value, field_name):
    try:
        return datetime.strptime(str(value), '%Y-%m-%d').date()
    except (TypeError, ValueError):
        raise ValueError(f'Invalid date for {field_name}. Use YYYY-MM-DD.')


def _organization_from_request(request, required=True):
    scoped_org = getattr(request, '_v1_organization', None)
    header_value = request.headers.get('X-Organization-Id')

    if scoped_org is not None:
        if header_value:
            header_org_id = _parse_public_id(header_value, 'org')
            if scoped_org.pk != header_org_id:
                raise PermissionError('X-Organization-Id does not match authenticated organization.')
        return scoped_org

    if not header_value:
        if required:
            raise ValueError('X-Organization-Id header is required.')
        return None

    org_id = _parse_public_id(header_value, 'org')
    queryset = _accessible_organizations_queryset(request.user)
    try:
        return queryset.get(pk=org_id)
    except Organization.DoesNotExist as exc:
        raise PermissionError('Organization not found or not accessible.') from exc


def _default_entity_for_org(organization):
    entity = organization.entities.order_by('id').first()
    if entity:
        return entity

    return Entity.objects.create(
        organization=organization,
        name=organization.name,
        country=organization.primary_country or 'US',
        entity_type='corporation',
        status='active',
        local_currency=organization.primary_currency or 'USD',
    )


def _financial_headers_or_cached_response(request, organization, endpoint):
    key = request.headers.get('X-Idempotency-Key')
    if not key:
        return None, Response(
            {'detail': 'X-Idempotency-Key header is required for financial POST endpoints.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    existing = IdempotencyKey.objects.filter(
        organization=organization,
        key=key,
        endpoint=endpoint,
    ).first()
    if existing:
        return None, Response(existing.response_body, status=existing.response_status)
    return key, None


def _store_idempotent_response(organization, key, endpoint, response):
    if not key:
        return
    IdempotencyKey.objects.create(
        organization=organization,
        key=key,
        endpoint=endpoint,
        response_body=response.data,
        response_status=response.status_code,
    )


def _source_metadata(request, extra=None):
    metadata = {
        'source': 'api_v1',
        'environment': current_api_environment(),
        'path': request.path,
    }
    remote_addr = request.META.get('REMOTE_ADDR')
    if remote_addr:
        metadata['ip_address'] = remote_addr
    if extra:
        metadata.update(extra)
    return metadata


def _error_code_from_status(status_code):
    return {
        400: 'INVALID_REQUEST',
        401: 'UNAUTHORIZED',
        403: 'FORBIDDEN',
        404: 'NOT_FOUND',
        405: 'METHOD_NOT_ALLOWED',
        429: 'RATE_LIMITED',
    }.get(status_code, 'INTERNAL_ERROR')


def _standard_error_payload(*, code, message, details=None):
    return {
        'error': {
            'code': code,
            'message': message,
            'details': details or {},
        }
    }


def _normalize_error_response_data(data, status_code):
    if isinstance(data, dict) and 'error' in data:
        return data

    if isinstance(data, dict) and 'detail' in data:
        detail = data.get('detail')
        detail_code = getattr(detail, 'code', None)
        code = {
            'throttled': 'RATE_LIMITED',
            'authentication_failed': 'UNAUTHORIZED',
            'not_authenticated': 'UNAUTHORIZED',
            'permission_denied': 'FORBIDDEN',
            'insufficient_scope': 'INSUFFICIENT_SCOPE',
            'not_found': 'NOT_FOUND',
        }.get(detail_code, _error_code_from_status(status_code))
        details = {key: value for key, value in data.items() if key != 'detail'}
        return _standard_error_payload(code=code, message=str(detail), details=details)

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
        return _standard_error_payload(
            code=_error_code_from_status(status_code),
            message=message,
            details=data,
        )

    return _standard_error_payload(
        code=_error_code_from_status(status_code),
        message=str(data),
        details={},
    )


def _normalize_masked_account_number(value):
    raw_value = str(value or '').strip()
    if not raw_value:
        return '****0000'

    digits = ''.join(character for character in raw_value if character.isdigit())
    if not digits:
        raise ValueError('account_number_masked must contain at least the last four digits.')
    if len(digits) > 4 and '*' not in raw_value:
        raise ValueError('Full account numbers must not be submitted. Only masked values are allowed.')
    return f"****{digits[-4:]}"


def _is_cash_account(account):
    account_name = (account.account_name or '').lower()
    return account.account_type == 'asset' and (
        account.account_code in {'1000', '1099'}
        or 'cash' in account_name
        or 'bank' in account_name
    )


def _audit(organization, user, action, model_name, object_id, changes=None, *, entity=None, ip_address=None):
    if not user or not getattr(user, 'is_authenticated', False):
        return
    AuditLog.objects.create(
        organization=organization,
        entity=entity,
        user=user,
        action=action,
        model_name=model_name,
        object_id=str(object_id),
        changes=changes or {},
        ip_address=ip_address,
    )


def _emit_event(organization, event_type, data):
    event_id = _public_id('evt', secrets.randbelow(10_000_000))
    payload = {
        'id': event_id,
        'type': event_type,
        'created_at': timezone.now().isoformat(),
        'data': data,
    }
    SystemEvent.objects.create(
        organization=organization,
        event_id=event_id,
        event_type=event_type,
        payload=payload,
        source_metadata={'source': 'api_v1'},
    )
    endpoints = WebhookEndpoint.objects.filter(organization=organization, is_active=True)
    for endpoint in endpoints:
        if event_type in (endpoint.events or []):
            _create_and_execute_delivery(endpoint=endpoint, event_type=event_type, event_id=event_id, payload=payload)
    return payload


def _create_and_execute_delivery(*, endpoint, event_type, event_id, payload):
    delivery = WebhookDelivery.objects.create(
        endpoint=endpoint,
        event_type=event_type,
        event_id=event_id,
        payload=payload,
        status='pending',
    )
    _execute_webhook_delivery(delivery)
    return delivery


def _execute_webhook_delivery(delivery):
    payload_bytes = json.dumps(delivery.payload, separators=(',', ':'), sort_keys=True).encode('utf-8')
    signature = hmac.new(
        (delivery.endpoint.secret or '').encode('utf-8'),
        payload_bytes,
        hashlib.sha256,
    ).hexdigest()
    request = Request(
        delivery.endpoint.url,
        data=payload_bytes,
        headers={
            'Content-Type': 'application/json',
            'X-LGX-Event': delivery.event_type,
            'X-LGX-Delivery-ID': delivery.event_id,
            'X-LGX-Signature-SHA256': f'sha256={signature}',
        },
        method='POST',
    )
    attempt_count = delivery.attempt_count
    while attempt_count < WEBHOOK_MAX_ATTEMPTS:
        attempt_count += 1
        attempt_time = timezone.now()
        try:
            with urlopen(request, timeout=10) as response:
                body = response.read().decode('utf-8', errors='replace')
                WebhookDelivery.objects.filter(pk=delivery.pk).update(
                    status='delivered',
                    response_status=getattr(response, 'status', 200),
                    response_body=body[:5000],
                    attempt_count=attempt_count,
                    last_attempt_at=attempt_time,
                    next_retry_at=None,
                    delivered_at=timezone.now(),
                )
                return
        except HTTPError as exc:
            body = exc.read().decode('utf-8', errors='replace') if hasattr(exc, 'read') else str(exc)
            next_retry_at = attempt_time + timedelta(seconds=2 ** attempt_count) if attempt_count < WEBHOOK_MAX_ATTEMPTS else None
            WebhookDelivery.objects.filter(pk=delivery.pk).update(
                status='pending' if next_retry_at else 'failed',
                response_status=exc.code,
                response_body=body[:5000],
                attempt_count=attempt_count,
                last_attempt_at=attempt_time,
                next_retry_at=next_retry_at,
            )
        except (URLError, OSError, TimeoutError) as exc:
            next_retry_at = attempt_time + timedelta(seconds=2 ** attempt_count) if attempt_count < WEBHOOK_MAX_ATTEMPTS else None
            WebhookDelivery.objects.filter(pk=delivery.pk).update(
                status='pending' if next_retry_at else 'failed',
                response_body=str(exc)[:5000],
                attempt_count=attempt_count,
                last_attempt_at=attempt_time,
                next_retry_at=next_retry_at,
            )


def _system_event_payload(event):
    return {
        'id': event.event_id,
        'type': event.event_type,
        'created_at': event.created_at.isoformat(),
        'data': (event.payload or {}).get('data', {}),
    }


def _webhook_delivery_payload(delivery):
    return {
        'id': _public_id('wd', delivery.pk),
        'event_id': delivery.event_id,
        'event_type': delivery.event_type,
        'status': delivery.status,
        'response_status': delivery.response_status,
        'attempt_count': delivery.attempt_count,
        'last_attempt_at': delivery.last_attempt_at.isoformat() if delivery.last_attempt_at else None,
        'next_retry_at': delivery.next_retry_at.isoformat() if delivery.next_retry_at else None,
        'delivered_at': delivery.delivered_at.isoformat() if delivery.delivered_at else None,
        'created_at': delivery.created_at.isoformat(),
    }


def _oauth_application_payload(application, raw_secret=None):
    payload = {
        'id': _public_id('key', application.pk),
        'name': application.name,
        'client_id': application.client_id,
        'scopes': application.scopes,
        'environment': application.environment,
        'status': 'active' if application.is_active else 'revoked',
        'created_at': application.created_at.isoformat(),
        'updated_at': application.updated_at.isoformat(),
    }
    if raw_secret is not None:
        payload['client_secret'] = raw_secret
        payload['api_key'] = compose_cli_api_key(application.client_id, raw_secret)
    return payload


def _permission_payload(permission):
    return {
        'id': permission.pk,
        'code': permission.code,
        'label': permission.get_code_display(),
    }


def _role_payload(role):
    return {
        'id': _public_id('role', role.pk),
        'name': role.name,
        'code': role.code,
        'description': role.description,
        'permissions': [_permission_payload(permission) for permission in role.permissions.all().order_by('code')],
        'created_at': role.created_at.isoformat(),
    }


def _team_member_payload(member):
    scoped_entities = member.scoped_entities.all().order_by('name')
    return {
        'id': _public_id('tm', member.pk),
        'user': {
            'id': member.user.pk,
            'email': member.user.email,
            'username': member.user.username,
            'first_name': member.user.first_name,
            'last_name': member.user.last_name,
        },
        'role': _role_payload(member.role),
        'invitation_status': 'accepted' if member.accepted_at else 'pending',
        'scoped_entities': [
            {'id': _public_id('ent', entity.pk), 'name': entity.name}
            for entity in scoped_entities
        ],
        'is_active': member.is_active,
        'invited_at': member.invited_at.isoformat(),
        'accepted_at': member.accepted_at.isoformat() if member.accepted_at else None,
    }


def _find_or_create_account(entity, code, name, account_type, currency='USD'):
    account, _ = ChartOfAccounts.objects.get_or_create(
        entity=entity,
        account_code=code,
        defaults={
            'account_name': name,
            'account_type': account_type,
            'currency': currency,
            'status': 'active',
        },
    )
    return account


def _account_payload(account):
    return {
        'id': _public_id('acc', account.pk),
        'code': account.account_code,
        'name': account.account_name,
        'type': account.account_type,
        'currency': account.currency,
        'parent_account_id': _public_id('acc', account.parent_account_id) if account.parent_account_id else None,
        'is_active': account.status == 'active',
        'current_balance': float(account.current_balance),
        'opening_balance': float(account.opening_balance),
    }


def _bill_payload(bill):
    return {
        'id': _public_id('bill', bill.pk),
        'bill_number': bill.bill_number,
        'vendor_id': _public_id('ven', bill.vendor.pk),
        'issue_date': str(bill.bill_date),
        'due_date': str(bill.due_date),
        'currency': bill.currency,
        'subtotal': float(bill.subtotal),
        'tax_amount': float(bill.tax_amount),
        'total_amount': float(bill.total_amount),
        'paid_amount': float(bill.paid_amount),
        'outstanding_amount': float(bill.outstanding_amount),
        'status': bill.status,
    }


def _bank_account_payload(bank_account):
    return {
        'id': _public_id('bank', bank_account.pk),
        'provider': bank_account.provider,
        'provider_account_id': bank_account.provider_account_id,
        'name': bank_account.account_name,
        'currency': bank_account.currency,
        'status': 'active' if bank_account.is_active else 'inactive',
        'verification_status': bank_account.verification_status,
        'account_number_masked': bank_account.account_number,
        'created_at': bank_account.created_at.isoformat(),
        'updated_at': bank_account.updated_at.isoformat(),
    }


def _reconciliation_status(bank_transaction):
    match = getattr(bank_transaction, 'reconciliation_match', None)
    if not match:
        return 'unreconciled'
    if match.matched_amount < abs(bank_transaction.amount):
        return 'partially_reconciled'
    return 'reconciled'


def _bank_transaction_payload(bank_transaction):
    match = getattr(bank_transaction, 'reconciliation_match', None)
    return {
        'id': _public_id('txn', bank_transaction.pk),
        'external_id': bank_transaction.transaction_id,
        'date': str(bank_transaction.transaction_date.date()),
        'amount': float(bank_transaction.amount),
        'currency': bank_transaction.currency,
        'description': bank_transaction.description,
        'status': _reconciliation_status(bank_transaction),
        'matched_ledger_entry_id': _public_id('je', match.journal_entry_id) if match else None,
        'raw_data': bank_transaction.raw_data or {},
    }


def _reconciliation_payload(match):
    return {
        'id': _public_id('rec', match.pk),
        'bank_transaction_id': _public_id('txn', match.bank_transaction_id),
        'ledger_entry_id': _public_id('je', match.journal_entry_id),
        'match_type': match.match_type,
        'matched_amount': float(match.matched_amount),
        'status': _reconciliation_status(match.bank_transaction),
        'matched_at': match.matched_at.isoformat(),
    }


def _customer_payload(customer):
    return {
        'id': _public_id('cus', customer.pk),
        'name': customer.customer_name,
        'email': customer.email,
        'tax_id': customer.tax_id,
        'billing_address': {
            'line1': customer.address,
            'city': customer.city,
            'country': customer.country,
            'postal_code': customer.postal_code,
        },
        'currency': customer.currency,
        'status': customer.status,
        'created_at': customer.created_at.isoformat(),
    }


def _vendor_payload(vendor):
    return {
        'id': _public_id('ven', vendor.pk),
        'name': vendor.vendor_name,
        'email': vendor.email,
        'tax_id': vendor.tax_id,
        'billing_address': {
            'line1': vendor.address,
            'city': vendor.city,
            'country': vendor.country,
            'postal_code': vendor.postal_code,
        },
        'currency': vendor.currency,
        'status': vendor.status,
        'created_at': vendor.created_at.isoformat(),
    }


def _journal_entry_payload(journal_entry):
    ledger_rows = journal_entry.ledger_entries.select_related('debit_account', 'credit_account').all()
    lines = []
    for row in ledger_rows:
        lines.append({
            'account_id': _public_id('acc', row.debit_account_id),
            'type': 'debit',
            'amount': float(row.debit_amount),
            'currency': row.debit_account.currency,
        })
        lines.append({
            'account_id': _public_id('acc', row.credit_account_id),
            'type': 'credit',
            'amount': float(row.credit_amount),
            'currency': row.credit_account.currency,
        })
    return {
        'id': _public_id('je', journal_entry.pk),
        'reference': journal_entry.reference_number,
        'date': str(journal_entry.posting_date),
        'description': journal_entry.description,
        'status': journal_entry.status,
        'posted_at': journal_entry.approved_at.isoformat() if journal_entry.approved_at else None,
        'lines': lines,
    }


def _pair_lines(lines):
    if not lines:
        raise ValueError('Journal entry must include at least one debit and one credit line.')

    debits = []
    credits = []
    total_debits = Decimal('0')
    total_credits = Decimal('0')

    for line in lines:
        account_id = _parse_public_id(line.get('account_id'), 'acc')
        amount = _decimal(line.get('amount'), 'amount')
        side = (line.get('type') or '').lower()
        payload = {
            'account_id': account_id,
            'amount': amount,
            'currency': line.get('currency') or 'USD',
        }
        if side == 'debit':
            total_debits += amount
            debits.append(payload)
        elif side == 'credit':
            total_credits += amount
            credits.append(payload)
        else:
            raise ValueError('Each journal line requires type debit or credit.')

    if total_debits != total_credits:
        raise ValueError('Journal entry debits and credits must balance.')

    pairs = []
    debit_index = 0
    credit_index = 0
    while debit_index < len(debits) and credit_index < len(credits):
        debit_line = debits[debit_index]
        credit_line = credits[credit_index]
        matched_amount = min(debit_line['amount'], credit_line['amount'])
        pairs.append({
            'debit_account_id': debit_line['account_id'],
            'credit_account_id': credit_line['account_id'],
            'amount': matched_amount,
        })
        debit_line['amount'] -= matched_amount
        credit_line['amount'] -= matched_amount
        if debit_line['amount'] == 0:
            debit_index += 1
        if credit_line['amount'] == 0:
            credit_index += 1
    return pairs


def _post_journal_entry(*, entity, user, reference, posting_date, description, lines, metadata=None, memo=''):
    pairs = _pair_lines(lines)
    journal_entry = JournalEntry.objects.create(
        entity=entity,
        entry_type='automated' if metadata else 'manual',
        reference_number=reference,
        description=description,
        posting_date=posting_date,
        memo=memo,
        status='posted',
        created_by=user,
        approved_by=user,
        approved_at=timezone.now(),
    )

    touched_accounts = defaultdict(lambda: Decimal('0'))
    account_cache = {}
    for pair in pairs:
        debit_account = account_cache.setdefault(
            pair['debit_account_id'],
            ChartOfAccounts.objects.get(pk=pair['debit_account_id'], entity=entity),
        )
        credit_account = account_cache.setdefault(
            pair['credit_account_id'],
            ChartOfAccounts.objects.get(pk=pair['credit_account_id'], entity=entity),
        )
        GeneralLedger.objects.create(
            entity=entity,
            debit_account=debit_account,
            credit_account=credit_account,
            debit_amount=pair['amount'],
            credit_amount=pair['amount'],
            description=description,
            reference_number=reference,
            posting_date=posting_date,
            journal_entry=journal_entry,
            posting_status='posted',
        )
        touched_accounts[debit_account.pk] += pair['amount']
        touched_accounts[credit_account.pk] -= pair['amount']

    for account_id, delta in touched_accounts.items():
        ChartOfAccounts.objects.filter(pk=account_id).update(current_balance=F('current_balance') + delta)

    return journal_entry


def _trial_balance_lines(entity, as_of_date=None):
    queryset = GeneralLedger.objects.filter(entity=entity, posting_status='posted')
    if as_of_date:
        queryset = queryset.filter(posting_date__lte=as_of_date)

    totals = defaultdict(lambda: {'debit': Decimal('0'), 'credit': Decimal('0'), 'account': None})
    for row in queryset.select_related('debit_account', 'credit_account'):
        debit_bucket = totals[row.debit_account_id]
        debit_bucket['account'] = row.debit_account
        debit_bucket['debit'] += row.debit_amount

        credit_bucket = totals[row.credit_account_id]
        credit_bucket['account'] = row.credit_account
        credit_bucket['credit'] += row.credit_amount

    lines = []
    for bucket in totals.values():
        account = bucket['account']
        lines.append({
            'account_code': account.account_code,
            'account_name': account.account_name,
            'debit': float(bucket['debit']),
            'credit': float(bucket['credit']),
        })
    lines.sort(key=lambda item: item['account_code'])
    return lines


def _profit_and_loss(entity, start_date, end_date):
    queryset = GeneralLedger.objects.filter(
        entity=entity,
        posting_status='posted',
        posting_date__gte=start_date,
        posting_date__lte=end_date,
    ).select_related('debit_account', 'credit_account')

    revenue = Decimal('0')
    expenses = Decimal('0')
    line_map = defaultdict(lambda: {'account_name': '', 'amount': Decimal('0')})

    for row in queryset:
        if row.credit_account.account_type == 'revenue':
            revenue += row.credit_amount
            line_map[row.credit_account.account_code]['account_name'] = row.credit_account.account_name
            line_map[row.credit_account.account_code]['amount'] += row.credit_amount
        if row.debit_account.account_type == 'expense':
            expenses += row.debit_amount
            line_map[row.debit_account.account_code]['account_name'] = row.debit_account.account_name
            line_map[row.debit_account.account_code]['amount'] -= row.debit_amount

    lines = []
    for account_code, bucket in sorted(line_map.items()):
        lines.append({
            'account_code': account_code,
            'account_name': bucket['account_name'],
            'amount': float(bucket['amount']),
        })

    return {
        'from_date': str(start_date),
        'to_date': str(end_date),
        'lines': lines,
        'total_revenue': float(revenue),
        'total_expenses': float(expenses),
        'net_income': float(revenue - expenses),
    }


def _account_balance_snapshot(entity, as_of_date=None):
    queryset = GeneralLedger.objects.filter(entity=entity, posting_status='posted')
    if as_of_date:
        queryset = queryset.filter(posting_date__lte=as_of_date)

    totals = defaultdict(lambda: {'debit': Decimal('0'), 'credit': Decimal('0'), 'account': None})
    for row in queryset.select_related('debit_account', 'credit_account'):
        debit_bucket = totals[row.debit_account_id]
        debit_bucket['account'] = row.debit_account
        debit_bucket['debit'] += row.debit_amount

        credit_bucket = totals[row.credit_account_id]
        credit_bucket['account'] = row.credit_account
        credit_bucket['credit'] += row.credit_amount
    return totals


def _balance_sheet(entity, as_of_date):
    snapshots = _account_balance_snapshot(entity, as_of_date)
    grouped = {
        'assets': [],
        'liabilities': [],
        'equity': [],
    }
    totals = {
        'assets': Decimal('0'),
        'liabilities': Decimal('0'),
        'equity': Decimal('0'),
    }

    for bucket in snapshots.values():
        account = bucket['account']
        if account.account_type not in {'asset', 'liability', 'equity'}:
            continue

        if account.account_type == 'asset':
            balance = bucket['debit'] - bucket['credit']
            group = 'assets'
        elif account.account_type == 'liability':
            balance = bucket['credit'] - bucket['debit']
            group = 'liabilities'
        else:
            balance = bucket['credit'] - bucket['debit']
            group = 'equity'

        if balance == 0:
            continue
        totals[group] += balance
        grouped[group].append(
            {
                'account_code': account.account_code,
                'account_name': account.account_name,
                'balance': float(balance),
            }
        )

    for lines in grouped.values():
        lines.sort(key=lambda item: item['account_code'])

    return {
        'as_of_date': str(as_of_date),
        'assets': grouped['assets'],
        'liabilities': grouped['liabilities'],
        'equity': grouped['equity'],
        'total_assets': float(totals['assets']),
        'total_liabilities': float(totals['liabilities']),
        'total_equity': float(totals['equity']),
    }


def _cash_flow_statement(entity, start_date, end_date):
    queryset = GeneralLedger.objects.filter(
        entity=entity,
        posting_status='posted',
        posting_date__gte=start_date,
        posting_date__lte=end_date,
    ).select_related('debit_account', 'credit_account')

    totals = {
        'operating': Decimal('0'),
        'investing': Decimal('0'),
        'financing': Decimal('0'),
    }

    for row in queryset:
        if _is_cash_account(row.debit_account):
            cash_effect = row.debit_amount
            counterparty = row.credit_account
        elif _is_cash_account(row.credit_account):
            cash_effect = -row.credit_amount
            counterparty = row.debit_account
        else:
            continue

        if counterparty.account_type in {'revenue', 'expense'}:
            bucket = 'operating'
        elif counterparty.account_type == 'asset':
            bucket = 'investing'
        else:
            bucket = 'financing'
        totals[bucket] += cash_effect

    return {
        'from_date': str(start_date),
        'to_date': str(end_date),
        'lines': [
            {'section': 'operating', 'amount': float(totals['operating'])},
            {'section': 'investing', 'amount': float(totals['investing'])},
            {'section': 'financing', 'amount': float(totals['financing'])},
        ],
        'net_cash_flow': float(totals['operating'] + totals['investing'] + totals['financing']),
    }


def _financial_account_defaults(entity, currency):
    return {
        'ar': _find_or_create_account(entity, '1100', 'Accounts Receivable', 'asset', currency),
        'ap': _find_or_create_account(entity, '2000', 'Accounts Payable', 'liability', currency),
        'cash': _find_or_create_account(entity, '1000', 'Cash', 'asset', currency),
        'bank_clearing': _find_or_create_account(entity, '1099', 'Bank Clearing', 'asset', currency),
        'revenue': _find_or_create_account(entity, '4000', 'Revenue', 'revenue', currency),
        'expense': _find_or_create_account(entity, '5000', 'Operating Expense', 'expense', currency),
    }


def _historical_lines_to_journal_payload(entity, currency, payload):
    balance_sheet = payload.get('balance_sheet') or []
    profit_and_loss = payload.get('profit_and_loss') or []
    if not balance_sheet and not profit_and_loss:
        raise ValueError('historical financials require balance_sheet or profit_and_loss lines.')

    retained_earnings = _find_or_create_account(
        entity,
        payload.get('retained_earnings_account_code') or '3200',
        payload.get('retained_earnings_account_name') or 'Retained Earnings',
        'equity',
        currency,
    )

    lines = []
    for raw_line in balance_sheet:
        amount = _decimal(raw_line.get('amount') or 0, 'balance_sheet.amount')
        if amount <= 0:
            continue
        side = (raw_line.get('side') or '').lower()
        if side not in {'debit', 'credit'}:
            raise ValueError('Each balance_sheet line must specify side debit or credit.')
        account = _find_or_create_account(
            entity,
            (raw_line.get('account_code') or '').strip(),
            (raw_line.get('account_name') or '').strip() or (raw_line.get('account_code') or '').strip(),
            (raw_line.get('account_type') or '').strip(),
            (raw_line.get('currency') or currency).strip(),
        )
        lines.append({
            'account_id': _public_id('acc', account.pk),
            'type': side,
            'amount': amount,
            'currency': account.currency,
        })

    net_income = Decimal('0')
    for raw_line in profit_and_loss:
        amount = _decimal(raw_line.get('amount') or 0, 'profit_and_loss.amount')
        account_type = (raw_line.get('account_type') or '').strip()
        account = _find_or_create_account(
            entity,
            (raw_line.get('account_code') or '').strip(),
            (raw_line.get('account_name') or '').strip() or (raw_line.get('account_code') or '').strip(),
            account_type,
            (raw_line.get('currency') or currency).strip(),
        )
        if account_type == 'revenue':
            net_income += amount
        elif account_type == 'expense':
            net_income -= amount
        else:
            raise ValueError('profit_and_loss lines must use account_type revenue or expense.')

    if net_income != 0:
        lines.append({
            'account_id': _public_id('acc', retained_earnings.pk),
            'type': 'credit' if net_income > 0 else 'debit',
            'amount': abs(net_income),
            'currency': retained_earnings.currency,
        })

    debit_total = sum(line['amount'] for line in lines if line['type'] == 'debit')
    credit_total = sum(line['amount'] for line in lines if line['type'] == 'credit')
    if debit_total != credit_total:
        raise ValueError('Historical financials must balance after retained earnings is applied.')

    return lines, retained_earnings, net_income


class V1BaseAPIView(APIView):
    permission_classes = [IsAuthenticated, APIKeyScopePermission]
    throttle_classes = [V1OrganizationBurstThrottle, V1OrganizationEndpointThrottle]

    def handle_exception(self, exc):
        if isinstance(exc, ValueError):
            return Response(_standard_error_payload(code='INVALID_REQUEST', message=str(exc), details={}), status=status.HTTP_400_BAD_REQUEST)
        if isinstance(exc, PermissionError):
            return Response(_standard_error_payload(code='FORBIDDEN', message=str(exc), details={}), status=status.HTTP_403_FORBIDDEN)
        if isinstance(exc, Http404):
            return Response(_standard_error_payload(code='NOT_FOUND', message='Resource not found.', details={}), status=status.HTTP_404_NOT_FOUND)
        if isinstance(exc, (AuthenticationFailed, NotAuthenticated, PermissionDenied, Throttled, ValidationError)):
            response = super().handle_exception(exc)
            if response is not None:
                response.data = _normalize_error_response_data(response.data, response.status_code)
            return response
        return super().handle_exception(exc)

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        if getattr(response, 'status_code', 200) >= 400 and hasattr(response, 'data'):
            response.data = _normalize_error_response_data(response.data, response.status_code)
            response._is_rendered = False
        return response

    def organization(self, request, required=True):
        return _organization_from_request(request, required=required)

    def entity(self, organization):
        return _default_entity_for_org(organization)


class V1PublicAPIView(APIView):
    permission_classes = [AllowAny]

    def handle_exception(self, exc):
        if isinstance(exc, ValueError):
            return Response(_standard_error_payload(code='INVALID_REQUEST', message=str(exc), details={}), status=status.HTTP_400_BAD_REQUEST)
        if isinstance(exc, Http404):
            return Response(_standard_error_payload(code='NOT_FOUND', message='Resource not found.', details={}), status=status.HTTP_404_NOT_FOUND)
        if isinstance(exc, (AuthenticationFailed, NotAuthenticated, PermissionDenied, Throttled, ValidationError)):
            response = super().handle_exception(exc)
            if response is not None:
                response.data = _normalize_error_response_data(response.data, response.status_code)
            return response
        return super().handle_exception(exc)

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        if getattr(response, 'status_code', 200) >= 400 and hasattr(response, 'data'):
            response.data = _normalize_error_response_data(response.data, response.status_code)
            response._is_rendered = False
        return response


class OpenAPISchemaView(V1PublicAPIView):
    def get(self, request):
        if not OPENAPI_SPEC_PATH.exists():
            raise Http404()
        return HttpResponse(OPENAPI_SPEC_PATH.read_text(), content_type='application/yaml; charset=utf-8')


class RedocView(V1PublicAPIView):
    def get(self, request):
        html = """<!DOCTYPE html>
<html lang=\"en\">
    <head>
        <meta charset=\"utf-8\" />
        <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
        <title>Ledgora API Docs</title>
        <style>
            body { margin: 0; padding: 0; }
        </style>
    </head>
    <body>
        <redoc spec-url=\"/v1/openapi.yaml\"></redoc>
        <script src=\"https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js\"></script>
    </body>
</html>
"""
        return HttpResponse(html, content_type='text/html; charset=utf-8')


class SwaggerUIView(V1PublicAPIView):
    def get(self, request):
        html = """<!DOCTYPE html>
<html lang="en">
    <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>Ledgora API Swagger</title>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css" />
        <style>
            body { margin: 0; background: #fafafa; }
            #swagger-ui { max-width: 1400px; margin: 0 auto; }
        </style>
    </head>
    <body>
        <div id="swagger-ui"></div>
        <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
        <script>
            window.ui = SwaggerUIBundle({
                url: '/v1/openapi.yaml',
                dom_id: '#swagger-ui',
                deepLinking: true,
                displayRequestDuration: true,
                persistAuthorization: true,
            });
        </script>
    </body>
</html>
"""
        return HttpResponse(html, content_type='text/html; charset=utf-8')


class AuthTokenView(V1PublicAPIView):

    def post(self, request):
        payload = request.data or {}
        if payload.get('grant_type') != 'client_credentials':
            return Response(
                {'detail': 'Only grant_type=client_credentials is supported.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        application = validate_client_credentials(
            payload.get('client_id', ''),
            payload.get('client_secret', ''),
        )
        return Response(issue_access_token(application), status=status.HTTP_200_OK)


class APIKeysView(V1BaseAPIView):
    def get(self, request):
        organization = self.organization(request)
        applications = organization.oauth_applications.order_by('-created_at')
        return Response([_oauth_application_payload(application) for application in applications])

    @transaction.atomic
    def post(self, request):
        organization = self.organization(request)
        payload = request.data or {}
        name = (payload.get('name') or '').strip()
        if not name:
            return Response({'detail': 'name is required.'}, status=status.HTTP_400_BAD_REQUEST)

        scopes = payload.get('scopes') or []
        if not isinstance(scopes, list):
            return Response({'detail': 'scopes must be an array.'}, status=status.HTTP_400_BAD_REQUEST)

        client_id = f"cli_{secrets.token_urlsafe(18)}"
        raw_secret = secrets.token_urlsafe(32)
        application = OAuthApplication.objects.create(
            organization=organization,
            name=name,
            client_id=client_id,
            client_secret_hash=_sha256(raw_secret),
            scopes=scopes,
            environment=current_api_environment(),
            source_metadata=_source_metadata(request, {'credential_type': 'api_key'}),
            is_active=True,
            created_by=request.user,
            updated_by=request.user,
        )
        _audit(organization, request.user, 'create', 'OAuthApplication', application.pk, payload)
        return Response(_oauth_application_payload(application, raw_secret=raw_secret), status=status.HTTP_201_CREATED)


class APIKeyRotateView(V1BaseAPIView):
    @transaction.atomic
    def post(self, request, key_id):
        organization = self.organization(request)
        application = get_object_or_404(OAuthApplication, pk=_parse_public_id(key_id, 'key'), organization=organization)
        raw_secret = secrets.token_urlsafe(32)
        application.client_secret_hash = _sha256(raw_secret)
        application.updated_by = request.user
        application.source_metadata = {
            **(application.source_metadata or {}),
            'last_rotated_at': timezone.now().isoformat(),
        }
        application.save(update_fields=['client_secret_hash', 'updated_by', 'source_metadata', 'updated_at'])
        _audit(organization, request.user, 'rotate', 'OAuthApplication', application.pk, {'scopes': application.scopes})
        return Response(_oauth_application_payload(application, raw_secret=raw_secret), status=status.HTTP_200_OK)


class APIKeyRevokeView(V1BaseAPIView):
    @transaction.atomic
    def post(self, request, key_id):
        organization = self.organization(request)
        application = get_object_or_404(OAuthApplication, pk=_parse_public_id(key_id, 'key'), organization=organization)
        application.is_active = False
        application.updated_by = request.user
        application.save(update_fields=['is_active', 'updated_by', 'updated_at'])
        application.api_keys.filter(is_revoked=False).update(
            is_revoked=True,
            revoked_at=timezone.now(),
            revoked_by=request.user,
            updated_at=timezone.now(),
        )
        _audit(organization, request.user, 'revoke', 'OAuthApplication', application.pk)
        return Response({'id': _public_id('key', application.pk), 'status': 'revoked'}, status=status.HTTP_200_OK)


class RolesView(V1BaseAPIView):
    def get(self, request):
        Role.get_or_create_default_roles()
        return Response([_role_payload(role) for role in Role.objects.all().prefetch_related('permissions').order_by('name')])


class PermissionsView(V1BaseAPIView):
    def get(self, request):
        Role.get_or_create_default_roles()
        return Response([_permission_payload(permission) for permission in Permission.objects.all().order_by('code')])


class TeamMembersView(V1BaseAPIView):
    def get(self, request):
        organization = self.organization(request)
        queryset = organization.team_members.select_related('user', 'role').prefetch_related('role__permissions', 'scoped_entities').order_by('-created_at')
        return Response([_team_member_payload(member) for member in queryset])

    @transaction.atomic
    def post(self, request):
        return self._invite(request)

    def _invite(self, request):
        organization = self.organization(request)
        if organization.owner_id != request.user.id:
            return Response({'detail': 'Only the organization owner can manage team members.'}, status=status.HTTP_403_FORBIDDEN)

        payload = request.data or {}
        email = (payload.get('email') or '').strip().lower()
        role_code = (payload.get('role_code') or '').strip()
        if not email or not role_code:
            return Response({'detail': 'email and role_code are required.'}, status=status.HTTP_400_BAD_REQUEST)

        Role.get_or_create_default_roles()
        role = get_object_or_404(Role, code=role_code)
        user = User.objects.filter(email=email).first()
        if user is None:
            base_username = slugify(email.split('@')[0]) or 'user'
            username = base_username
            suffix = 1
            while User.objects.filter(username=username).exists():
                suffix += 1
                username = f'{base_username}-{suffix}'
            user = User.objects.create_user(
                username=username,
                email=email,
                password=secrets.token_urlsafe(16),
                first_name=(payload.get('first_name') or '').strip(),
                last_name=(payload.get('last_name') or '').strip(),
            )
            user.set_unusable_password()
            user.save(update_fields=['password'])

        member, created = TeamMember.objects.get_or_create(
            organization=organization,
            user=user,
            defaults={
                'role': role,
                'is_active': True,
                'accepted_at': None,
            },
        )
        if not created and member.is_active and member.accepted_at:
            return Response({'detail': 'This user is already an active team member.'}, status=status.HTTP_400_BAD_REQUEST)

        if not created:
            member.role = role
            member.is_active = True
            member.accepted_at = None
            member.save(update_fields=['role', 'is_active', 'accepted_at', 'updated_at'])

        scoped_entity_ids = payload.get('scoped_entity_ids') or []
        if scoped_entity_ids:
            entities = Entity.objects.filter(
                organization=organization,
                pk__in=[_parse_public_id(value, 'ent') for value in scoped_entity_ids],
            )
            member.scoped_entities.set(entities)
        elif role.code != 'EXTERNAL_ADVISOR':
            member.scoped_entities.clear()

        _audit(organization, request.user, 'create' if created else 'update', 'TeamMember', member.pk, payload)
        member.refresh_from_db()
        response_payload = _team_member_payload(member)
        response_payload['invitation_sent'] = True
        return Response(response_payload, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class TeamMemberInviteView(TeamMembersView):
    @transaction.atomic
    def post(self, request):
        return self._invite(request)


class GlobalWorkspaceInviteView(V1BaseAPIView):
    @transaction.atomic
    def post(self, request):
        payload = request.data or {}
        workspace_ref = payload.get('workspace_id')
        workspace_id = WorkspaceService.resolve_workspace_id(workspace_ref)
        PermissionService.assert_owner_or_admin(workspace_id, request.user)

        email = (payload.get('email') or '').strip().lower()
        user_id = payload.get('user_id')
        if not email and user_id in [None, '']:
            return Response({'detail': 'email or user_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

        user = None
        if user_id not in [None, '']:
            try:
                user = User.objects.get(pk=int(user_id))
            except (TypeError, ValueError, User.DoesNotExist):
                return Response({'detail': 'user_id is invalid.'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            user = User.objects.filter(email=email).first()
            if user is None:
                base_username = slugify(email.split('@')[0]) or 'user'
                username = base_username
                suffix = 1
                while User.objects.filter(username=username).exists():
                    suffix += 1
                    username = f'{base_username}-{suffix}'
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=secrets.token_urlsafe(16),
                )
                user.set_unusable_password()
                user.save(update_fields=['password'])

        membership = WorkspaceMember.objects.filter(workspace_id=workspace_id, user=user).first()
        if membership and membership.role is not None and membership.status == ParticipantStatus.ACCEPTED:
            return Response({'detail': 'This user is already a workspace member.'}, status=status.HTTP_400_BAD_REQUEST)

        invited = MemberService.invite_member(workspace_id, request.user, user)
        response_data = {
            'workspace_id': str(workspace_id),
            'user': {
                'id': invited.user_id,
                'email': invited.user.email,
                'username': invited.user.username,
            },
            'status': invited.status,
            'role': invited.role,
            'invitation_sent': True,
        }
        return Response(response_data, status=status.HTTP_201_CREATED)


class TeamMemberDeactivateView(V1BaseAPIView):
    @transaction.atomic
    def post(self, request, team_member_id):
        organization = self.organization(request)
        if organization.owner_id != request.user.id:
            return Response({'detail': 'Only the organization owner can manage team members.'}, status=status.HTTP_403_FORBIDDEN)

        member = get_object_or_404(
            TeamMember.objects.select_related('user', 'role').prefetch_related('role__permissions', 'scoped_entities'),
            pk=_parse_public_id(team_member_id, 'tm'),
            organization=organization,
        )
        member.is_active = False
        member.save(update_fields=['is_active', 'updated_at'])
        _audit(organization, request.user, 'update', 'TeamMember', member.pk, {'deactivated': True})
        payload = _team_member_payload(member)
        payload['deactivated'] = True
        return Response(payload, status=status.HTTP_200_OK)


class OrganizationsView(V1BaseAPIView):
    def get(self, request):
        organizations = _accessible_organizations_queryset(request.user)
        data = [
            {
                'id': _public_id('org', organization.pk),
                'name': organization.name,
                'status': 'active',
                'country': organization.primary_country,
                'currency': organization.primary_currency,
                'created_at': organization.created_at.isoformat(),
            }
            for organization in organizations
        ]
        return Response(data)

    @transaction.atomic
    def post(self, request):
        payload = request.data or {}
        name = (payload.get('name') or '').strip()
        if not name:
            return Response({'detail': 'name is required.'}, status=status.HTTP_400_BAD_REQUEST)

        slug_base = slugify(name) or f'org-{request.user.pk}'
        slug = slug_base
        suffix = 1
        while Organization.objects.filter(slug=slug).exists():
            suffix += 1
            slug = f'{slug_base}-{suffix}'

        organization = Organization.objects.create(
            owner=request.user,
            name=name,
            slug=slug,
            industry=(payload.get('industry') or '').strip(),
            primary_country=(payload.get('country') or 'US').strip(),
            primary_currency=(payload.get('currency') or 'USD').strip(),
            settings={
                'legal_name': (payload.get('legal_name') or name).strip(),
                'timezone': (payload.get('timezone') or 'UTC').strip(),
                'api_version': 'v1',
            },
        )
        _default_entity_for_org(organization)
        _audit(organization, request.user, 'create', 'Organization', organization.pk, payload)
        return Response(
            {
                'id': _public_id('org', organization.pk),
                'name': organization.name,
                'status': 'active',
                'created_at': organization.created_at.isoformat(),
            },
            status=status.HTTP_201_CREATED,
        )


class MigrationJobsView(V1BaseAPIView):
    def post(self, request):
        organization = self.organization(request)
        entity = self.entity(organization)
        payload = request.data or {}
        job_type = payload.get('type')
        if not job_type:
            return Response({'detail': 'type is required.'}, status=status.HTTP_400_BAD_REQUEST)

        job = MigrationJob.objects.create(
            organization=organization,
            entity=entity,
            type=job_type,
            source_system=(payload.get('source_system') or 'other'),
            file_url=(payload.get('file_url') or '').strip(),
            status='pending',
            created_by=request.user,
            updated_by=request.user,
            metadata=_source_metadata(request),
        )
        _audit(organization, request.user, 'create', 'MigrationJob', job.pk, payload)
        return Response(
            {
                'id': _public_id('mig', job.pk),
                'type': job.type,
                'status': job.status,
                'created_at': job.created_at.isoformat(),
            },
            status=status.HTTP_201_CREATED,
        )


class MigrationJobDetailView(V1BaseAPIView):
    def get(self, request, job_id):
        organization = self.organization(request)
        job = get_object_or_404(MigrationJob, pk=_parse_public_id(job_id, 'mig'), organization=organization)
        return Response(
            {
                'id': _public_id('mig', job.pk),
                'type': job.type,
                'status': job.status,
                'processed_records': job.processed_records,
                'failed_records': job.failed_records,
                'error_report_url': job.file_url if job.failed_records else '',
            }
        )


class BulkMigrationBaseView(V1BaseAPIView):
    collection_key = None

    def post(self, request):
        organization = self.organization(request)
        entity = self.entity(organization)
        payload = request.data or {}
        records = payload.get(self.collection_key)
        if not isinstance(records, list):
            return Response(
                {'detail': f'{self.collection_key} must be an array.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        result = self.bulk_upsert(entity, request.user, records)
        _audit(organization, request.user, 'bulk_upsert', self.__class__.__name__, entity.pk, {'count': len(records)})
        return Response(result, status=status.HTTP_200_OK)

    def bulk_upsert(self, entity, user, records):
        raise NotImplementedError


class MigrationChartOfAccountsView(BulkMigrationBaseView):
    collection_key = 'accounts'

    def bulk_upsert(self, entity, user, records):
        created = 0
        updated = 0
        errors = []
        for index, record in enumerate(records):
            try:
                code = (record.get('code') or '').strip()
                name = (record.get('name') or '').strip()
                account_type = (record.get('type') or '').strip()
                if not code or not name or not account_type:
                    raise ValueError('code, name, and type are required.')
                account, was_created = ChartOfAccounts.objects.update_or_create(
                    entity=entity,
                    account_code=code,
                    defaults={
                        'account_name': name,
                        'account_type': account_type,
                        'currency': (record.get('currency') or entity.local_currency or 'USD').strip(),
                        'status': 'active' if record.get('is_active', True) else 'inactive',
                        'description': record.get('external_id') or '',
                    },
                )
                created += int(was_created)
                updated += int(not was_created)
            except Exception as exc:
                errors.append({'index': index, 'detail': str(exc)})
        return {
            'created': created,
            'updated': updated,
            'failed': len(errors),
            'errors': errors,
        }


class MigrationCustomersView(BulkMigrationBaseView):
    collection_key = 'customers'

    def bulk_upsert(self, entity, user, records):
        created = 0
        updated = 0
        errors = []
        for index, record in enumerate(records):
            try:
                name = (record.get('name') or '').strip()
                email = (record.get('email') or '').strip() or f'customer-{index}@example.com'
                external_id = (record.get('external_id') or '').strip()
                code = external_id or slugify(name or f'customer-{index}')[:50].upper() or f'CUST{index + 1}'
                address = record.get('billing_address') or {}
                customer, was_created = Customer.objects.update_or_create(
                    entity=entity,
                    customer_code=code,
                    defaults={
                        'customer_name': name,
                        'email': email,
                        'tax_id': (record.get('tax_id') or '').strip(),
                        'address': (address.get('line1') or '').strip(),
                        'city': (address.get('city') or '').strip(),
                        'country': (address.get('country') or '').strip(),
                        'postal_code': (address.get('postal_code') or '').strip(),
                        'currency': (record.get('currency') or entity.local_currency or 'USD').strip(),
                        'status': 'active',
                    },
                )
                created += int(was_created)
                updated += int(not was_created)
            except Exception as exc:
                errors.append({'index': index, 'detail': str(exc)})
        return {'created': created, 'updated': updated, 'failed': len(errors), 'errors': errors}


class MigrationVendorsView(BulkMigrationBaseView):
    collection_key = 'vendors'

    def bulk_upsert(self, entity, user, records):
        created = 0
        updated = 0
        errors = []
        for index, record in enumerate(records):
            try:
                name = (record.get('name') or '').strip()
                email = (record.get('email') or '').strip() or f'vendor-{index}@example.com'
                external_id = (record.get('external_id') or '').strip()
                code = external_id or slugify(name or f'vendor-{index}')[:50].upper() or f'VEN{index + 1}'
                address = record.get('billing_address') or {}
                vendor, was_created = Vendor.objects.update_or_create(
                    entity=entity,
                    vendor_code=code,
                    defaults={
                        'vendor_name': name,
                        'email': email,
                        'tax_id': (record.get('tax_id') or '').strip(),
                        'address': (address.get('line1') or '').strip(),
                        'city': (address.get('city') or '').strip(),
                        'country': (address.get('country') or '').strip(),
                        'postal_code': (address.get('postal_code') or '').strip(),
                        'currency': (record.get('currency') or entity.local_currency or 'USD').strip(),
                        'status': 'active',
                    },
                )
                created += int(was_created)
                updated += int(not was_created)
            except Exception as exc:
                errors.append({'index': index, 'detail': str(exc)})
        return {'created': created, 'updated': updated, 'failed': len(errors), 'errors': errors}


class MigrationInvoicesView(BulkMigrationBaseView):
    collection_key = 'invoices'

    def bulk_upsert(self, entity, user, records):
        created = 0
        updated = 0
        errors = []
        accounts = _financial_account_defaults(entity, entity.local_currency or 'USD')
        for index, record in enumerate(records):
            try:
                customer_id = _parse_public_id(record.get('customer_id'), 'cus') if record.get('customer_id') else None
                customer = Customer.objects.get(pk=customer_id, entity=entity) if customer_id else entity.customers.order_by('id').first()
                if not customer:
                    raise ValueError('customer_id is required when no customers exist.')
                invoice_number = (record.get('external_id') or record.get('invoice_number') or f'MIG-INV-{index + 1}').strip()
                subtotal = _decimal(record.get('subtotal') or record.get('total_amount') or 0, 'subtotal')
                tax_amount = _decimal(record.get('tax_amount') or 0, 'tax_amount')
                total_amount = _decimal(record.get('total_amount') or (subtotal + tax_amount), 'total_amount')
                invoice, was_created = Invoice.objects.update_or_create(
                    entity=entity,
                    invoice_number=invoice_number,
                    defaults={
                        'customer': customer,
                        'invoice_date': _date(record.get('issue_date') or record.get('invoice_date') or timezone.now().date(), 'issue_date'),
                        'due_date': _date(record.get('due_date') or timezone.now().date(), 'due_date'),
                        'subtotal': subtotal,
                        'tax_amount': tax_amount,
                        'total_amount': total_amount,
                        'paid_amount': _decimal(record.get('paid_amount') or 0, 'paid_amount'),
                        'outstanding_amount': _decimal(record.get('outstanding_amount') or total_amount, 'outstanding_amount'),
                        'currency': (record.get('currency') or entity.local_currency or 'USD').strip(),
                        'status': (record.get('status') or 'posted').strip(),
                        'description': (record.get('description') or '').strip(),
                        'notes': 'Imported via v1 migration endpoint',
                        'created_by': user,
                    },
                )
                if was_created:
                    _post_journal_entry(
                        entity=entity,
                        user=user,
                        reference=invoice.invoice_number,
                        posting_date=invoice.invoice_date,
                        description=f'Imported invoice {invoice.invoice_number}',
                        lines=[
                            {'account_id': _public_id('acc', accounts['ar'].pk), 'type': 'debit', 'amount': total_amount, 'currency': invoice.currency},
                            {'account_id': _public_id('acc', accounts['revenue'].pk), 'type': 'credit', 'amount': total_amount, 'currency': invoice.currency},
                        ],
                        metadata={'source': 'migration', 'invoice_id': invoice.pk},
                    )
                created += int(was_created)
                updated += int(not was_created)
            except Exception as exc:
                errors.append({'index': index, 'detail': str(exc)})
        return {'created': created, 'updated': updated, 'failed': len(errors), 'errors': errors}


class MigrationBillsView(BulkMigrationBaseView):
    collection_key = 'bills'

    def bulk_upsert(self, entity, user, records):
        created = 0
        updated = 0
        errors = []
        accounts = _financial_account_defaults(entity, entity.local_currency or 'USD')
        for index, record in enumerate(records):
            try:
                vendor_id = _parse_public_id(record.get('vendor_id'), 'ven') if record.get('vendor_id') else None
                vendor = Vendor.objects.get(pk=vendor_id, entity=entity) if vendor_id else entity.vendors.order_by('id').first()
                if not vendor:
                    raise ValueError('vendor_id is required when no vendors exist.')
                bill_number = (record.get('external_id') or record.get('bill_number') or f'MIG-BILL-{index + 1}').strip()
                subtotal = _decimal(record.get('subtotal') or record.get('total_amount') or 0, 'subtotal')
                tax_amount = _decimal(record.get('tax_amount') or 0, 'tax_amount')
                total_amount = _decimal(record.get('total_amount') or (subtotal + tax_amount), 'total_amount')
                bill, was_created = Bill.objects.update_or_create(
                    entity=entity,
                    bill_number=bill_number,
                    defaults={
                        'vendor': vendor,
                        'bill_date': _date(record.get('bill_date') or timezone.now().date(), 'bill_date'),
                        'due_date': _date(record.get('due_date') or timezone.now().date(), 'due_date'),
                        'subtotal': subtotal,
                        'tax_amount': tax_amount,
                        'total_amount': total_amount,
                        'paid_amount': _decimal(record.get('paid_amount') or 0, 'paid_amount'),
                        'outstanding_amount': _decimal(record.get('outstanding_amount') or total_amount, 'outstanding_amount'),
                        'currency': (record.get('currency') or entity.local_currency or 'USD').strip(),
                        'status': (record.get('status') or 'posted').strip(),
                        'description': (record.get('description') or '').strip(),
                        'notes': 'Imported via v1 migration endpoint',
                        'created_by': user,
                    },
                )
                if was_created:
                    _post_journal_entry(
                        entity=entity,
                        user=user,
                        reference=bill.bill_number,
                        posting_date=bill.bill_date,
                        description=f'Imported bill {bill.bill_number}',
                        lines=[
                            {'account_id': _public_id('acc', accounts['expense'].pk), 'type': 'debit', 'amount': total_amount, 'currency': bill.currency},
                            {'account_id': _public_id('acc', accounts['ap'].pk), 'type': 'credit', 'amount': total_amount, 'currency': bill.currency},
                        ],
                        metadata={'source': 'migration', 'bill_id': bill.pk},
                    )
                created += int(was_created)
                updated += int(not was_created)
            except Exception as exc:
                errors.append({'index': index, 'detail': str(exc)})
        return {'created': created, 'updated': updated, 'failed': len(errors), 'errors': errors}


class MigrationTransactionsView(BulkMigrationBaseView):
    collection_key = 'transactions'

    def bulk_upsert(self, entity, user, records):
        created = 0
        updated = 0
        errors = []
        account, _ = BookkeepingAccount.objects.get_or_create(
            entity=entity,
            name='Imported Clearing',
            defaults={
                'type': 'bank',
                'currency': entity.local_currency or 'USD',
                'balance': 0,
            },
        )
        for index, record in enumerate(records):
            try:
                amount = _decimal(record.get('amount') or 0, 'amount')
                txn_type = 'expense' if amount < 0 else 'income'
                category, _ = BookkeepingCategory.objects.get_or_create(
                    entity=entity,
                    name='Imported Transactions',
                    type=txn_type,
                    defaults={'description': 'Imported via Ledgora API v1'},
                )
                reference = (record.get('external_id') or record.get('reference') or f'MIG-TXN-{index + 1}').strip()
                transaction_obj, was_created = Transaction.objects.update_or_create(
                    entity=entity,
                    reference_number=reference,
                    defaults={
                        'type': txn_type,
                        'category': category,
                        'account': account,
                        'amount': abs(amount),
                        'currency': (record.get('currency') or entity.local_currency or 'USD').strip(),
                        'payment_method': 'bank',
                        'description': (record.get('description') or 'Imported transaction').strip(),
                        'date': _date(record.get('date') or timezone.now().date(), 'date'),
                        'created_by': user,
                    },
                )
                created += int(was_created)
                updated += int(not was_created)
            except Exception as exc:
                errors.append({'index': index, 'detail': str(exc)})
        return {'created': created, 'updated': updated, 'failed': len(errors), 'errors': errors}


class MigrationOpeningBalancesView(BulkMigrationBaseView):
    collection_key = 'balances'

    @transaction.atomic
    def bulk_upsert(self, entity, user, records):
        created = 0
        errors = []
        currency = entity.local_currency or 'USD'
        equity_account = _find_or_create_account(entity, '3000', 'Opening Balance Equity', 'equity', currency)
        for index, record in enumerate(records):
            try:
                account = ChartOfAccounts.objects.get(entity=entity, account_code=(record.get('account_code') or '').strip())
                amount = _decimal(record.get('amount') or 0, 'amount')
                direction = (record.get('type') or 'debit').lower()
                ChartOfAccounts.objects.filter(pk=account.pk).update(
                    opening_balance=amount,
                    current_balance=Decimal('0'),
                )
                _post_journal_entry(
                    entity=entity,
                    user=user,
                    reference=f'OPEN-{account.account_code}',
                    posting_date=_date(record.get('date') or timezone.now().date(), 'date'),
                    description=f'Opening balance for {account.account_name}',
                    lines=[
                        {'account_id': _public_id('acc', account.pk), 'type': direction, 'amount': amount, 'currency': currency},
                        {'account_id': _public_id('acc', equity_account.pk), 'type': 'credit' if direction == 'debit' else 'debit', 'amount': amount, 'currency': currency},
                    ],
                    metadata={'source': 'migration', 'opening_balance': True},
                )
                created += 1
            except Exception as exc:
                errors.append({'index': index, 'detail': str(exc)})
        return {'created': created, 'updated': 0, 'failed': len(errors), 'errors': errors}


class AccountsView(V1BaseAPIView):
    def get(self, request):
        organization = self.organization(request)
        entity = self.entity(organization)
        data = [_account_payload(account) for account in entity.chart_of_accounts.order_by('account_code')]
        return Response(data)

    def post(self, request):
        organization = self.organization(request)
        entity = self.entity(organization)
        payload = request.data or {}
        code = (payload.get('code') or '').strip()
        name = (payload.get('name') or '').strip()
        account_type = (payload.get('type') or '').strip()
        if not code or not name or not account_type:
            return Response({'detail': 'code, name, and type are required.'}, status=status.HTTP_400_BAD_REQUEST)

        parent_id = _parse_public_id(payload.get('parent_account_id'), 'acc') if payload.get('parent_account_id') else None
        parent = ChartOfAccounts.objects.filter(entity=entity, pk=parent_id).first() if parent_id else None
        account = ChartOfAccounts.objects.create(
            entity=entity,
            account_code=code,
            account_name=name,
            account_type=account_type,
            parent_account=parent,
            currency=(payload.get('currency') or entity.local_currency or 'USD').strip(),
            status='active' if payload.get('is_active', True) else 'inactive',
            description=(payload.get('subtype') or '').strip(),
        )
        _audit(organization, request.user, 'create', 'ChartOfAccounts', account.pk, payload)
        return Response(_account_payload(account), status=status.HTTP_201_CREATED)


class CustomersView(V1BaseAPIView):
    def get(self, request):
        organization = self.organization(request)
        entity = self.entity(organization)
        return Response([_customer_payload(customer) for customer in entity.customers.order_by('customer_name')])

    def post(self, request):
        organization = self.organization(request)
        entity = self.entity(organization)
        payload = request.data or {}
        name = (payload.get('name') or '').strip()
        email = (payload.get('email') or '').strip()
        if not name or not email:
            return Response({'detail': 'name and email are required.'}, status=status.HTTP_400_BAD_REQUEST)
        address = payload.get('billing_address') or {}
        customer = Customer.objects.create(
            entity=entity,
            customer_code=slugify(name)[:50].upper() or f'CUST-{timezone.now().timestamp()}',
            customer_name=name,
            email=email,
            tax_id=(payload.get('tax_id') or '').strip(),
            address=(address.get('line1') or '').strip(),
            city=(address.get('city') or '').strip(),
            country=(address.get('country') or '').strip(),
            postal_code=(address.get('postal_code') or '').strip(),
            currency=entity.local_currency or 'USD',
            status='active',
        )
        _audit(organization, request.user, 'create', 'Customer', customer.pk, payload)
        return Response(_customer_payload(customer), status=status.HTTP_201_CREATED)


class VendorsView(V1BaseAPIView):
    def get(self, request):
        organization = self.organization(request)
        entity = self.entity(organization)
        return Response([_vendor_payload(vendor) for vendor in entity.vendors.order_by('vendor_name')])

    def post(self, request):
        organization = self.organization(request)
        entity = self.entity(organization)
        payload = request.data or {}
        name = (payload.get('name') or '').strip()
        email = (payload.get('email') or '').strip()
        if not name or not email:
            return Response({'detail': 'name and email are required.'}, status=status.HTTP_400_BAD_REQUEST)
        address = payload.get('billing_address') or {}
        vendor = Vendor.objects.create(
            entity=entity,
            vendor_code=slugify(name)[:50].upper() or f'VEN-{timezone.now().timestamp()}',
            vendor_name=name,
            email=email,
            tax_id=(payload.get('tax_id') or '').strip(),
            address=(address.get('line1') or '').strip(),
            city=(address.get('city') or '').strip(),
            country=(address.get('country') or '').strip(),
            postal_code=(address.get('postal_code') or '').strip(),
            currency=entity.local_currency or 'USD',
            status='active',
        )
        _audit(organization, request.user, 'create', 'Vendor', vendor.pk, payload)
        return Response(_vendor_payload(vendor), status=status.HTTP_201_CREATED)


class JournalEntriesView(V1BaseAPIView):
    def get(self, request):
        organization = self.organization(request)
        entity = self.entity(organization)
        queryset = entity.journal_entries.filter(status='posted').order_by('-posting_date', '-created_at')
        if request.query_params.get('from_date'):
            queryset = queryset.filter(posting_date__gte=_date(request.query_params.get('from_date'), 'from_date'))
        if request.query_params.get('to_date'):
            queryset = queryset.filter(posting_date__lte=_date(request.query_params.get('to_date'), 'to_date'))
        if request.query_params.get('reference'):
            queryset = queryset.filter(reference_number__icontains=request.query_params.get('reference'))
        if request.query_params.get('account_id'):
            account_id = _parse_public_id(request.query_params.get('account_id'), 'acc')
            queryset = queryset.filter(Q(ledger_entries__debit_account_id=account_id) | Q(ledger_entries__credit_account_id=account_id)).distinct()
        page_size = int(request.query_params.get('page_size') or 100)
        page = max(int(request.query_params.get('page') or 1), 1)
        start = (page - 1) * page_size
        end = start + page_size
        items = [_journal_entry_payload(entry) for entry in queryset[start:end]]
        return Response({'results': items, 'page': page, 'page_size': page_size, 'count': queryset.count()})

    @transaction.atomic
    def post(self, request):
        organization = self.organization(request)
        entity = self.entity(organization)
        idempotency_key, cached = _financial_headers_or_cached_response(request, organization, 'POST:/v1/ledger/journal-entries')
        if cached:
            return cached
        payload = request.data or {}
        journal_entry = _post_journal_entry(
            entity=entity,
            user=request.user,
            reference=(payload.get('reference') or f'JE-{timezone.now().strftime("%Y%m%d%H%M%S")}').strip(),
            posting_date=_date(payload.get('date') or timezone.now().date(), 'date'),
            description=(payload.get('description') or '').strip() or 'Journal entry',
            lines=payload.get('lines') or [],
            metadata=payload.get('metadata') or {},
        )
        _audit(organization, request.user, 'create', 'JournalEntry', journal_entry.pk, payload)
        response = Response(
            {
                'id': _public_id('je', journal_entry.pk),
                'status': 'posted',
                'posted_at': journal_entry.approved_at.isoformat() if journal_entry.approved_at else None,
            },
            status=status.HTTP_201_CREATED,
        )
        _store_idempotent_response(organization, idempotency_key, 'POST:/v1/ledger/journal-entries', response)
        _emit_event(
            organization,
            FINANCIAL_EVENT_SOURCES['journal_entries.post'],
            {'journal_entry_id': _public_id('je', journal_entry.pk), 'reference': journal_entry.reference_number},
        )
        return response


class InvoicesView(V1BaseAPIView):
    @transaction.atomic
    def post(self, request):
        organization = self.organization(request)
        entity = self.entity(organization)
        idempotency_key, cached = _financial_headers_or_cached_response(request, organization, 'POST:/v1/invoices')
        if cached:
            return cached
        payload = request.data or {}
        customer = get_object_or_404(Customer, pk=_parse_public_id(payload.get('customer_id'), 'cus'), entity=entity)
        issue_date = _date(payload.get('issue_date') or timezone.now().date(), 'issue_date')
        due_date = _date(payload.get('due_date') or issue_date, 'due_date')
        currency = (payload.get('currency') or entity.local_currency or 'USD').strip()
        line_items = payload.get('line_items') or []
        if not line_items:
            return Response({'detail': 'line_items is required.'}, status=status.HTTP_400_BAD_REQUEST)

        subtotal = Decimal('0')
        for line in line_items:
            quantity = _decimal(line.get('quantity') or 0, 'quantity')
            unit_price = _decimal(line.get('unit_price') or 0, 'unit_price')
            subtotal += quantity * unit_price
        tax_amount = Decimal('0')
        for tax in payload.get('taxes') or []:
            tax_rate = _decimal(tax.get('rate') or 0, 'taxes.rate')
            tax_amount += subtotal * tax_rate
        total_amount = subtotal + tax_amount

        invoice = Invoice.objects.create(
            entity=entity,
            customer=customer,
            invoice_number=f'INV-{timezone.now().strftime("%Y%m%d%H%M%S")}',
            invoice_date=issue_date,
            due_date=due_date,
            subtotal=subtotal,
            tax_amount=tax_amount,
            total_amount=total_amount,
            paid_amount=Decimal('0'),
            outstanding_amount=total_amount,
            currency=currency,
            status='posted',
            description='; '.join((line.get('description') or '').strip() for line in line_items if line.get('description')),
            notes='Created via Ledgora API v1',
            created_by=request.user,
        )
        for line in line_items:
            quantity = _decimal(line.get('quantity') or 0, 'quantity')
            unit_price = _decimal(line.get('unit_price') or 0, 'unit_price')
            InvoiceLineItem.objects.create(
                invoice=invoice,
                description=(line.get('description') or '').strip() or 'Invoice line item',
                quantity=quantity,
                unit_price=unit_price,
                tax_rate=Decimal('0'),
                line_amount=quantity * unit_price,
            )

        accounts = _financial_account_defaults(entity, currency)
        revenue_account_id = _parse_public_id(line_items[0].get('revenue_account_id'), 'acc') if line_items[0].get('revenue_account_id') else accounts['revenue'].pk
        revenue_account = ChartOfAccounts.objects.filter(entity=entity, pk=revenue_account_id).first() or accounts['revenue']
        journal_entry = _post_journal_entry(
            entity=entity,
            user=request.user,
            reference=invoice.invoice_number,
            posting_date=issue_date,
            description=f'Invoice to {customer.customer_name}',
            lines=[
                {'account_id': _public_id('acc', accounts['ar'].pk), 'type': 'debit', 'amount': total_amount, 'currency': currency},
                {'account_id': _public_id('acc', revenue_account.pk), 'type': 'credit', 'amount': total_amount, 'currency': currency},
            ],
            metadata={'source': 'invoicing', 'invoice_id': invoice.pk},
        )

        _audit(organization, request.user, 'create', 'Invoice', invoice.pk, payload)
        event_payload = _emit_event(
            organization,
            FINANCIAL_EVENT_SOURCES['invoices.create'],
            {'invoice_id': _public_id('inv', invoice.pk), 'amount': float(total_amount), 'currency': currency},
        )
        response = Response(
            {
                'id': _public_id('inv', invoice.pk),
                'invoice_number': invoice.invoice_number,
                'status': invoice.status,
                'customer_id': _public_id('cus', customer.pk),
                'issue_date': str(invoice.invoice_date),
                'due_date': str(invoice.due_date),
                'currency': invoice.currency,
                'subtotal': float(invoice.subtotal),
                'tax_amount': float(invoice.tax_amount),
                'total_amount': float(invoice.total_amount),
                'journal_entry_id': _public_id('je', journal_entry.pk),
                'webhook_event_id': event_payload['id'],
            },
            status=status.HTTP_201_CREATED,
        )
        _store_idempotent_response(organization, idempotency_key, 'POST:/v1/invoices', response)
        return response


class BillsView(V1BaseAPIView):
    def get(self, request):
        organization = self.organization(request)
        entity = self.entity(organization)
        queryset = entity.bills.select_related('vendor').order_by('-bill_date', '-created_at')
        return Response([_bill_payload(bill) for bill in queryset])

    @transaction.atomic
    def post(self, request):
        organization = self.organization(request)
        entity = self.entity(organization)
        idempotency_key, cached = _financial_headers_or_cached_response(request, organization, 'POST:/v1/bills')
        if cached:
            return cached

        payload = request.data or {}
        vendor = get_object_or_404(Vendor, pk=_parse_public_id(payload.get('vendor_id'), 'ven'), entity=entity)
        issue_date = _date(payload.get('issue_date') or timezone.now().date(), 'issue_date')
        due_date = _date(payload.get('due_date') or issue_date, 'due_date')
        currency = (payload.get('currency') or entity.local_currency or 'USD').strip()
        line_items = payload.get('line_items') or []
        if not line_items:
            return Response({'detail': 'line_items is required.'}, status=status.HTTP_400_BAD_REQUEST)

        subtotal = Decimal('0')
        for line in line_items:
            quantity = _decimal(line.get('quantity') or 0, 'quantity')
            unit_price = _decimal(line.get('unit_price') or 0, 'unit_price')
            subtotal += quantity * unit_price
        tax_amount = Decimal('0')
        for tax in payload.get('taxes') or []:
            tax_rate = _decimal(tax.get('rate') or 0, 'taxes.rate')
            tax_amount += subtotal * tax_rate
        total_amount = subtotal + tax_amount

        bill = Bill.objects.create(
            entity=entity,
            vendor=vendor,
            bill_number=f'BILL-{timezone.now().strftime("%Y%m%d%H%M%S")}',
            bill_date=issue_date,
            due_date=due_date,
            subtotal=subtotal,
            tax_amount=tax_amount,
            total_amount=total_amount,
            paid_amount=Decimal('0'),
            outstanding_amount=total_amount,
            currency=currency,
            status='posted',
            description='; '.join((line.get('description') or '').strip() for line in line_items if line.get('description')),
            notes='Created via Ledgora API v1',
            created_by=request.user,
        )

        accounts = _financial_account_defaults(entity, currency)
        expense_account_id = _parse_public_id(line_items[0].get('expense_account_id'), 'acc') if line_items[0].get('expense_account_id') else accounts['expense'].pk
        expense_account = ChartOfAccounts.objects.filter(entity=entity, pk=expense_account_id).first() or accounts['expense']
        journal_entry = _post_journal_entry(
            entity=entity,
            user=request.user,
            reference=bill.bill_number,
            posting_date=issue_date,
            description=f'Bill from {vendor.vendor_name}',
            lines=[
                {'account_id': _public_id('acc', expense_account.pk), 'type': 'debit', 'amount': total_amount, 'currency': currency},
                {'account_id': _public_id('acc', accounts['ap'].pk), 'type': 'credit', 'amount': total_amount, 'currency': currency},
            ],
            metadata={'source': 'accounts_payable', 'bill_id': bill.pk},
        )

        _audit(organization, request.user, 'create', 'Bill', bill.pk, payload)
        event_payload = _emit_event(
            organization,
            FINANCIAL_EVENT_SOURCES['bills.create'],
            {
                'bill_id': _public_id('bill', bill.pk),
                'vendor_id': _public_id('ven', vendor.pk),
                'amount': float(bill.total_amount),
                'currency': currency,
            },
        )
        response = Response(
            {
                **_bill_payload(bill),
                'journal_entry_id': _public_id('je', journal_entry.pk),
                'webhook_event_id': event_payload['id'],
            },
            status=status.HTTP_201_CREATED,
        )
        _store_idempotent_response(organization, idempotency_key, 'POST:/v1/bills', response)
        return response


class BillPaymentsView(V1BaseAPIView):
    @transaction.atomic
    def post(self, request, bill_id):
        organization = self.organization(request)
        entity = self.entity(organization)
        idempotency_key, cached = _financial_headers_or_cached_response(request, organization, f'POST:/v1/bills/{bill_id}/payments')
        if cached:
            return cached

        payload = request.data or {}
        bill = get_object_or_404(Bill, pk=_parse_public_id(bill_id, 'bill'), entity=entity)
        payment_date = _date(payload.get('payment_date') or timezone.now().date(), 'payment_date')
        amount = _decimal(payload.get('amount') or 0, 'amount')
        currency = (payload.get('currency') or bill.currency or entity.local_currency or 'USD').strip()
        payment = BillPayment.objects.create(
            entity=entity,
            bill=bill,
            vendor=bill.vendor,
            payment_date=payment_date,
            amount=amount,
            payment_method=(payload.get('payment_method') or 'bank_transfer').strip(),
            reference_number=(payload.get('reference_number') or '').strip(),
        )
        bill.paid_amount += amount
        bill.outstanding_amount = max(bill.total_amount - bill.paid_amount, Decimal('0'))
        bill.status = 'paid' if bill.outstanding_amount == 0 else 'partially_paid'
        bill.save(update_fields=['paid_amount', 'outstanding_amount', 'status', 'updated_at'])

        accounts = _financial_account_defaults(entity, currency)
        cash_account = accounts['cash']
        bank_account_id = _parse_public_id(payload.get('bank_account_id'), 'bank') if payload.get('bank_account_id') else None
        if bank_account_id:
            bank_account = get_object_or_404(BankAccount, pk=bank_account_id, entity=entity)
            bank_account.balance -= amount
            bank_account.available_balance -= amount
            bank_account.save(update_fields=['balance', 'available_balance', 'updated_at'])
            cash_account.account_name = bank_account.account_name
            cash_account.save(update_fields=['account_name', 'updated_at'])

        journal_entry = _post_journal_entry(
            entity=entity,
            user=request.user,
            reference=f'{bill.bill_number}-PAY',
            posting_date=payment_date,
            description=f'Payment for {bill.bill_number}',
            lines=[
                {'account_id': _public_id('acc', accounts['ap'].pk), 'type': 'debit', 'amount': amount, 'currency': currency},
                {'account_id': _public_id('acc', cash_account.pk), 'type': 'credit', 'amount': amount, 'currency': currency},
            ],
            metadata={'source': 'bill_payment', 'bill_id': bill.pk, 'payment_id': payment.pk},
        )
        event_payload = _emit_event(
            organization,
            FINANCIAL_EVENT_SOURCES['bills.payment'],
            {
                'bill_id': _public_id('bill', bill.pk),
                'amount': float(amount),
                'currency': currency,
            },
        )
        response = Response(
            {
                'id': _public_id('billpay', payment.pk),
                'bill_id': _public_id('bill', bill.pk),
                'payment_date': str(payment.payment_date),
                'amount': float(payment.amount),
                'currency': currency,
                'status': bill.status,
                'journal_entry_id': _public_id('je', journal_entry.pk),
                'webhook_event_id': event_payload['id'],
            },
            status=status.HTTP_201_CREATED,
        )
        _store_idempotent_response(organization, idempotency_key, f'POST:/v1/bills/{bill_id}/payments', response)
        _audit(organization, request.user, 'create', 'BillPayment', payment.pk, payload)
        return response


class InvoicePaymentsView(V1BaseAPIView):
    @transaction.atomic
    def post(self, request, invoice_id):
        organization = self.organization(request)
        entity = self.entity(organization)
        idempotency_key, cached = _financial_headers_or_cached_response(request, organization, f'POST:/v1/invoices/{invoice_id}/payments')
        if cached:
            return cached
        payload = request.data or {}
        invoice = get_object_or_404(Invoice, pk=_parse_public_id(invoice_id, 'inv'), entity=entity)
        payment_date = _date(payload.get('payment_date') or timezone.now().date(), 'payment_date')
        amount = _decimal(payload.get('amount') or 0, 'amount')
        currency = (payload.get('currency') or invoice.currency or entity.local_currency or 'USD').strip()
        payment = Payment.objects.create(
            entity=entity,
            invoice=invoice,
            customer=invoice.customer,
            payment_date=payment_date,
            amount=amount,
            payment_method=(payload.get('payment_method') or 'bank_transfer').strip(),
            reference_number=(payload.get('reference_number') or '').strip(),
        )
        invoice.paid_amount += amount
        invoice.outstanding_amount = max(invoice.total_amount - invoice.paid_amount, Decimal('0'))
        if invoice.outstanding_amount == 0:
            invoice.status = 'paid'
        else:
            invoice.status = 'partially_paid'
        invoice.save(update_fields=['paid_amount', 'outstanding_amount', 'status', 'updated_at'])

        accounts = _financial_account_defaults(entity, currency)
        bank_account_id = _parse_public_id(payload.get('bank_account_id'), 'bank') if payload.get('bank_account_id') else None
        cash_account = accounts['cash']
        if bank_account_id:
            bank_account = get_object_or_404(BankAccount, pk=bank_account_id, entity=entity)
            bank_account.balance += amount
            bank_account.available_balance += amount
            bank_account.save(update_fields=['balance', 'available_balance', 'updated_at'])
            cash_account.account_name = bank_account.account_name
            cash_account.save(update_fields=['account_name', 'updated_at'])
        journal_entry = _post_journal_entry(
            entity=entity,
            user=request.user,
            reference=f'{invoice.invoice_number}-PAY',
            posting_date=payment_date,
            description=f'Payment for {invoice.invoice_number}',
            lines=[
                {'account_id': _public_id('acc', cash_account.pk), 'type': 'debit', 'amount': amount, 'currency': currency},
                {'account_id': _public_id('acc', accounts['ar'].pk), 'type': 'credit', 'amount': amount, 'currency': currency},
            ],
            metadata={'source': 'invoice_payment', 'invoice_id': invoice.pk, 'payment_id': payment.pk},
        )
        event_payload = _emit_event(
            organization,
            FINANCIAL_EVENT_SOURCES['invoices.payment'],
            {
                'invoice_id': _public_id('inv', invoice.pk),
                'amount': float(amount),
                'currency': currency,
            },
        )
        response = Response(
            {
                'id': _public_id('pay', payment.pk),
                'invoice_id': _public_id('inv', invoice.pk),
                'payment_date': str(payment.payment_date),
                'amount': float(payment.amount),
                'currency': currency,
                'status': invoice.status,
                'journal_entry_id': _public_id('je', journal_entry.pk),
                'webhook_event_id': event_payload['id'],
            },
            status=status.HTTP_201_CREATED,
        )
        _store_idempotent_response(organization, idempotency_key, f'POST:/v1/invoices/{invoice_id}/payments', response)
        _audit(organization, request.user, 'create', 'Payment', payment.pk, payload)
        return response


class BankAccountsView(V1BaseAPIView):
    def get(self, request):
        organization = self.organization(request)
        entity = self.entity(organization)
        queryset = entity.bank_accounts.order_by('bank_name', 'account_name')
        return Response([_bank_account_payload(bank_account) for bank_account in queryset])

    def post(self, request):
        organization = self.organization(request)
        entity = self.entity(organization)
        payload = request.data or {}
        provider = (payload.get('provider') or '').strip().lower()
        provider_account_id = (payload.get('provider_account_id') or '').strip()
        name = (payload.get('name') or '').strip()
        if not provider or not provider_account_id or not name:
            return Response(
                {'detail': 'provider, provider_account_id, and name are required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        masked_account_number = _normalize_masked_account_number(payload.get('account_number_masked'))
        bank_account, created = BankAccount.objects.get_or_create(
            entity=entity,
            provider=provider,
            provider_account_id=provider_account_id,
            defaults={
                'account_name': name,
                'account_number': masked_account_number,
                'bank_name': provider.title(),
                'account_type': 'business',
                'currency': (payload.get('currency') or entity.local_currency or 'USD').strip(),
                'verification_status': (payload.get('verification_status') or 'unverified').strip(),
                'notes': f'provider={provider};provider_account_id={provider_account_id}',
            },
        )
        if not created:
            bank_account.account_name = name
            bank_account.account_number = masked_account_number
            bank_account.currency = (payload.get('currency') or bank_account.currency or entity.local_currency or 'USD').strip()
            bank_account.verification_status = (payload.get('verification_status') or bank_account.verification_status or 'unverified').strip()
            bank_account.save(update_fields=['account_name', 'account_number', 'currency', 'verification_status', 'updated_at'])

        _audit(organization, request.user, 'create', 'BankAccount', bank_account.pk, payload, entity=entity)
        response_status = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(_bank_account_payload(bank_account), status=response_status)


class BankAccountTransactionsView(V1BaseAPIView):
    def get(self, request, bank_account_id):
        organization = self.organization(request)
        entity = self.entity(organization)
        bank_account = get_object_or_404(BankAccount, pk=_parse_public_id(bank_account_id, 'bank'), entity=entity)
        queryset = bank_account.bankingtransaction_set.order_by('-transaction_date', '-created_at').select_related('reconciliation_match__journal_entry')
        status_filter = (request.query_params.get('status') or '').strip().lower()
        payload = [_bank_transaction_payload(transaction) for transaction in queryset]
        if status_filter:
            payload = [transaction for transaction in payload if transaction['status'] == status_filter]
        return Response(payload)

    @transaction.atomic
    def post(self, request, bank_account_id):
        organization = self.organization(request)
        entity = self.entity(organization)
        bank_account = get_object_or_404(BankAccount, pk=_parse_public_id(bank_account_id, 'bank'), entity=entity)
        payload = request.data or {}
        return _import_bank_transactions(
            request=request,
            organization=organization,
            entity=entity,
            bank_account=bank_account,
            transactions=payload.get('transactions') or [],
            endpoint=f'POST:/v1/bank-accounts/{bank_account_id}/transactions',
            user=request.user,
        )


class ReconciliationMatchesView(V1BaseAPIView):
    def get(self, request):
        organization = self.organization(request)
        entity = self.entity(organization)
        queryset = ReconciliationMatch.objects.filter(entity=entity).select_related('bank_transaction', 'journal_entry').order_by('-matched_at')
        return Response([_reconciliation_payload(match) for match in queryset])

    @transaction.atomic
    def post(self, request):
        organization = self.organization(request)
        entity = self.entity(organization)
        payload = request.data or {}
        bank_transaction = get_object_or_404(
            BankingTransaction,
            pk=_parse_public_id(payload.get('bank_transaction_id'), 'txn'),
            entity=entity,
        )
        journal_entry = get_object_or_404(
            JournalEntry,
            pk=_parse_public_id(payload.get('ledger_entry_id'), 'je'),
            entity=entity,
            status='posted',
        )
        matched_amount = _decimal(payload.get('matched_amount') or abs(bank_transaction.amount), 'matched_amount')
        if matched_amount <= 0:
            return Response({'detail': 'matched_amount must be greater than zero.'}, status=status.HTTP_400_BAD_REQUEST)
        if matched_amount > abs(bank_transaction.amount):
            return Response({'detail': 'matched_amount cannot exceed the bank transaction amount.'}, status=status.HTTP_400_BAD_REQUEST)

        match, _ = ReconciliationMatch.objects.update_or_create(
            bank_transaction=bank_transaction,
            defaults={
                'entity': entity,
                'journal_entry': journal_entry,
                'match_type': (payload.get('match_type') or 'manual').strip(),
                'matched_amount': matched_amount,
                'notes': (payload.get('notes') or '').strip(),
                'matched_by': request.user,
            },
        )
        bank_transaction.is_matched = matched_amount >= abs(bank_transaction.amount)
        bank_transaction.save(update_fields=['is_matched', 'updated_at'])

        event_payload = _emit_event(
            organization,
            FINANCIAL_EVENT_SOURCES['reconciliation.match'],
            {
                'bank_transaction_id': _public_id('txn', bank_transaction.pk),
                'ledger_entry_id': _public_id('je', journal_entry.pk),
                'match_type': match.match_type,
                'matched_amount': float(match.matched_amount),
            },
        )
        _audit(organization, request.user, 'reconcile', 'ReconciliationMatch', match.pk, payload, entity=entity)
        return Response(
            {
                **_reconciliation_payload(match),
                'webhook_event_id': event_payload['id'],
            },
            status=status.HTTP_201_CREATED,
        )


class TrialBalanceView(V1BaseAPIView):
    def get(self, request):
        organization = self.organization(request)
        entity = self.entity(organization)
        as_of_date = _date(request.query_params.get('as_of_date') or timezone.now().date(), 'as_of_date')
        currency = (request.query_params.get('currency') or entity.local_currency or 'USD').strip()
        return Response(
            {
                'as_of_date': str(as_of_date),
                'currency': currency,
                'lines': _trial_balance_lines(entity, as_of_date),
            }
        )


class ProfitAndLossView(V1BaseAPIView):
    def get(self, request):
        organization = self.organization(request)
        entity = self.entity(organization)
        from_date = _date(request.query_params.get('from_date') or timezone.now().date().replace(month=1, day=1), 'from_date')
        to_date = _date(request.query_params.get('to_date') or timezone.now().date(), 'to_date')
        result = _profit_and_loss(entity, from_date, to_date)
        result['currency'] = (request.query_params.get('currency') or entity.local_currency or 'USD').strip()
        return Response(result)


class BalanceSheetView(V1BaseAPIView):
    def get(self, request):
        organization = self.organization(request)
        entity = self.entity(organization)
        as_of_date = _date(request.query_params.get('as_of_date') or timezone.now().date(), 'as_of_date')
        result = _balance_sheet(entity, as_of_date)
        result['currency'] = (request.query_params.get('currency') or entity.local_currency or 'USD').strip()
        return Response(result)


class CashFlowView(V1BaseAPIView):
    def get(self, request):
        organization = self.organization(request)
        entity = self.entity(organization)
        from_date = _date(request.query_params.get('from_date') or timezone.now().date().replace(month=1, day=1), 'from_date')
        to_date = _date(request.query_params.get('to_date') or timezone.now().date(), 'to_date')
        result = _cash_flow_statement(entity, from_date, to_date)
        result['currency'] = (request.query_params.get('currency') or entity.local_currency or 'USD').strip()
        return Response(result)


class SystemEventsView(V1BaseAPIView):
    def get(self, request):
        organization = self.organization(request)
        cutoff = timezone.now() - timedelta(days=30)
        queryset = organization.system_events.filter(created_at__gte=cutoff).order_by('-created_at')
        event_type = (request.query_params.get('event_type') or '').strip()
        if event_type:
            queryset = queryset.filter(event_type=event_type)
        return Response([_system_event_payload(event) for event in queryset])


class WebhookEndpointsView(V1BaseAPIView):
    def get(self, request):
        organization = self.organization(request)
        queryset = organization.webhook_endpoints.order_by('-created_at')
        return Response(
            [
                {
                    'id': _public_id('wh', endpoint.pk),
                    'url': endpoint.url,
                    'events': endpoint.events,
                    'is_active': endpoint.is_active,
                    'created_at': endpoint.created_at.isoformat(),
                }
                for endpoint in queryset
            ]
        )

    def post(self, request):
        organization = self.organization(request)
        payload = request.data or {}
        url = (payload.get('url') or '').strip()
        events = payload.get('events') or []
        if not url or not isinstance(events, list) or not events:
            return Response({'detail': 'url and events are required.'}, status=status.HTTP_400_BAD_REQUEST)
        endpoint = WebhookEndpoint.objects.create(
            organization=organization,
            url=url,
            events=events,
            secret=secrets.token_urlsafe(24),
            source_metadata=_source_metadata(request),
            is_active=True,
            created_by=request.user,
            updated_by=request.user,
        )
        _audit(organization, request.user, 'create', 'WebhookEndpoint', endpoint.pk, payload)
        return Response(
            {
                'id': _public_id('wh', endpoint.pk),
                'url': endpoint.url,
                'events': endpoint.events,
                'secret': endpoint.secret,
                'created_at': endpoint.created_at.isoformat(),
            },
            status=status.HTTP_201_CREATED,
        )


class WebhookDeliveriesView(V1BaseAPIView):
    def get(self, request):
        organization = self.organization(request)
        cutoff = timezone.now() - timedelta(days=30)
        queryset = WebhookDelivery.objects.filter(endpoint__organization=organization, created_at__gte=cutoff).select_related('endpoint').order_by('-created_at')
        endpoint_id = request.query_params.get('endpoint_id')
        if endpoint_id:
            queryset = queryset.filter(endpoint_id=_parse_public_id(endpoint_id, 'wh'))
        event_id = (request.query_params.get('event_id') or '').strip()
        if event_id:
            queryset = queryset.filter(event_id=event_id)
        return Response([_webhook_delivery_payload(delivery) for delivery in queryset])


class WebhookEventReplayView(V1BaseAPIView):
    @transaction.atomic
    def post(self, request, event_id):
        organization = self.organization(request)
        cutoff = timezone.now() - timedelta(days=30)
        event = get_object_or_404(SystemEvent, organization=organization, event_id=event_id, created_at__gte=cutoff)
        payload = request.data or {}
        endpoint_id = payload.get('endpoint_id')
        endpoints = [
            endpoint for endpoint in WebhookEndpoint.objects.filter(organization=organization, is_active=True).order_by('id')
            if event.event_type in (endpoint.events or [])
        ]
        if endpoint_id:
            endpoint_pk = _parse_public_id(endpoint_id, 'wh')
            endpoints = [endpoint for endpoint in endpoints if endpoint.pk == endpoint_pk]

        deliveries = []
        for endpoint in endpoints:
            deliveries.append(
                _create_and_execute_delivery(
                    endpoint=endpoint,
                    event_type=event.event_type,
                    event_id=event.event_id,
                    payload=event.payload,
                )
            )
        _audit(organization, request.user, 'replay', 'SystemEvent', event.event_id, payload)
        return Response(
            {
                'event_id': event.event_id,
                'replayed_count': len(deliveries),
                'deliveries': [_webhook_delivery_payload(delivery) for delivery in deliveries],
            },
            status=status.HTTP_200_OK,
        )


class MigrationBankStatementsView(V1BaseAPIView):
    @transaction.atomic
    def post(self, request):
        organization = self.organization(request)
        entity = self.entity(organization)
        payload = request.data or {}
        bank_account = get_object_or_404(
            BankAccount,
            pk=_parse_public_id(payload.get('bank_account_id'), 'bank'),
            entity=entity,
        )
        return _import_bank_transactions(
            request=request,
            organization=organization,
            entity=entity,
            bank_account=bank_account,
            transactions=payload.get('transactions') or [],
            endpoint='POST:/v1/migration/bank-statements',
            user=request.user,
        )


class MigrationHistoricalFinancialsView(V1BaseAPIView):
    @transaction.atomic
    def post(self, request):
        organization = self.organization(request)
        entity = self.entity(organization)
        idempotency_key, cached = _financial_headers_or_cached_response(request, organization, 'POST:/v1/migration/historical-financials')
        if cached:
            return cached

        payload = request.data or {}
        currency = (payload.get('currency') or entity.local_currency or 'USD').strip()
        as_of_date = _date(payload.get('as_of_date') or timezone.now().date(), 'as_of_date')
        lines, retained_earnings, net_income = _historical_lines_to_journal_payload(entity, currency, payload)
        journal_entry = _post_journal_entry(
            entity=entity,
            user=request.user,
            reference=(payload.get('reference') or f'HIST-{as_of_date.strftime("%Y%m%d")}').strip(),
            posting_date=as_of_date,
            description=(payload.get('description') or 'Historical financial import').strip(),
            lines=lines,
            metadata={'source': 'historical_financials', 'as_of_date': str(as_of_date)},
        )
        response = Response(
            {
                'id': _public_id('hist', journal_entry.pk),
                'journal_entry_id': _public_id('je', journal_entry.pk),
                'as_of_date': str(as_of_date),
                'currency': currency,
                'retained_earnings_account_id': _public_id('acc', retained_earnings.pk),
                'retained_earnings_amount': float(abs(net_income)),
                'retained_earnings_direction': 'credit' if net_income > 0 else 'debit' if net_income < 0 else 'none',
                'imported_lines': len(lines),
            },
            status=status.HTTP_201_CREATED,
        )
        _store_idempotent_response(organization, idempotency_key, 'POST:/v1/migration/historical-financials', response)
        _audit(organization, request.user, 'create', 'HistoricalFinancialImport', journal_entry.pk, payload)
        return response


def _import_bank_transactions(*, request, organization, entity, bank_account, transactions, endpoint, user):
    idempotency_key, cached = _financial_headers_or_cached_response(request, organization, endpoint)
    if cached:
        return cached

    accounts = _financial_account_defaults(entity, bank_account.currency or entity.local_currency or 'USD')
    imported = []
    for record in transactions:
        amount = _decimal(record.get('amount') or 0, 'amount')
        imported_txn, created = BankingTransaction.objects.get_or_create(
            entity=entity,
            bank_account=bank_account,
            transaction_id=(record.get('external_id') or f'{bank_account.pk}-{timezone.now().timestamp()}'),
            defaults={
                'transaction_date': timezone.make_aware(datetime.combine(_date(record.get('date') or timezone.now().date(), 'date'), datetime.min.time())),
                'amount': amount,
                'currency': (record.get('currency') or bank_account.currency).strip(),
                'description': (record.get('description') or 'Imported bank transaction').strip(),
                'counterparty_name': (record.get('counterparty_name') or 'Unknown').strip(),
                'counterparty_account': '',
                'transaction_type': 'debit' if amount < 0 else 'credit',
                'status': 'completed',
                'raw_data': record.get('raw_data') or {},
            },
        )
        if not created:
            continue

        bank_account.balance += amount
        bank_account.available_balance += amount
        lines = [
            {
                'account_id': _public_id('acc', accounts['cash'].pk if amount >= 0 else accounts['bank_clearing'].pk),
                'type': 'debit',
                'amount': abs(amount),
                'currency': imported_txn.currency,
            },
            {
                'account_id': _public_id('acc', accounts['bank_clearing'].pk if amount >= 0 else accounts['cash'].pk),
                'type': 'credit',
                'amount': abs(amount),
                'currency': imported_txn.currency,
            },
        ]
        _post_journal_entry(
            entity=entity,
            user=user,
            reference=f'BANK-{imported_txn.transaction_id}',
            posting_date=imported_txn.transaction_date.date(),
            description=f'Bank transaction import: {imported_txn.description}',
            lines=lines,
            metadata={'source': 'bank_import', 'bank_transaction_id': imported_txn.pk},
        )
        imported.append(imported_txn)

    bank_account.last_synced = timezone.now()
    bank_account.save(update_fields=['balance', 'available_balance', 'last_synced', 'updated_at'])
    event_payload = _emit_event(
        organization,
        FINANCIAL_EVENT_SOURCES['bank_transactions.import'],
        {'bank_account_id': _public_id('bank', bank_account.pk), 'count': len(imported)},
    )
    response = Response(
        {
            'bank_account_id': _public_id('bank', bank_account.pk),
            'imported_count': len(imported),
            'transactions': [_bank_transaction_payload(transaction) for transaction in imported],
            'webhook_event_id': event_payload['id'],
        },
        status=status.HTTP_201_CREATED,
    )
    _store_idempotent_response(organization, idempotency_key, endpoint, response)
    _audit(organization, user, 'bulk_import', 'BankingTransaction', bank_account.pk, {'count': len(imported)}, entity=entity)
    return response
