import os
import re
import uuid
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode

from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime

from .banking_security import decrypt_secret, encrypt_secret
from .models import (
    AuditLog,
    BankAccount,
    BankingCategorizationDecision,
    BankingCategorizationRule,
    BankingConsentLog,
    BankingIntegration,
    BankingSyncRun,
    BankingTransaction,
    BookkeepingCategory,
    Entity,
)


DEFAULT_CONSENT_SCOPES = ['accounts:read', 'transactions:read', 'balances:read']

PROVIDER_HINT_CATEGORY_MAP = {
    'coffee_shop': 'Food & Beverage',
    'food_and_drink': 'Food & Beverage',
    'food': 'Food & Beverage',
    'restaurants': 'Food & Beverage',
    'transportation': 'Transportation',
    'travel': 'Travel',
    'utilities': 'Utilities',
    'software': 'Software',
    'saas': 'Software',
    'payroll': 'Payroll',
    'insurance': 'Insurance',
    'bank_fees': 'Bank Fees',
    'marketing': 'Marketing',
}

MERCHANT_CATEGORY_MAP = {
    'starbucks': 'Food & Beverage',
    'uber eats': 'Food Delivery',
    'doordash': 'Food Delivery',
    'lyft': 'Transportation',
    'uber': 'Transportation',
    'aws': 'Software',
    'amazon web services': 'Software',
    'google workspace': 'Software',
    'slack': 'Software',
    'adobe': 'Software',
    'shell': 'Fuel',
    'chevron': 'Fuel',
    'at&t': 'Utilities',
    'verizon': 'Utilities',
}

DESCRIPTION_KEYWORDS = [
    (re.compile(r'utility|electric|water|internet|broadband', re.I), 'Utilities'),
    (re.compile(r'payroll|salary|wages', re.I), 'Payroll'),
    (re.compile(r'subscription|license|saas|software', re.I), 'Software'),
    (re.compile(r'flight|hotel|airbnb|travel', re.I), 'Travel'),
    (re.compile(r'fuel|gas station|petrol', re.I), 'Fuel'),
    (re.compile(r'insurance', re.I), 'Insurance'),
    (re.compile(r'meal|restaurant|cafe|coffee|lunch|dinner', re.I), 'Food & Beverage'),
    (re.compile(r'delivery|courier|shipment|freight', re.I), 'Logistics'),
    (re.compile(r'advert|campaign|marketing', re.I), 'Marketing'),
]

CATEGORY_BUCKET_MAP = {
    'bank fees': 'Treasury Ops',
    'food & beverage': 'Operating Expenses',
    'food delivery': 'Operating Expenses',
    'fuel': 'Transportation',
    'insurance': 'Risk & Compliance',
    'logistics': 'Operations',
    'marketing': 'Growth',
    'payroll': 'People Ops',
    'software': 'Technology',
    'transportation': 'Transportation',
    'travel': 'Travel',
    'utilities': 'Utilities',
    'uncategorized': 'Needs Review',
}


def _safe_decimal(value, default='0'):
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal(default)


def _safe_datetime(value):
    if isinstance(value, datetime):
        if timezone.is_naive(value):
            return timezone.make_aware(value)
        return value

    if isinstance(value, str) and value:
        parsed = parse_datetime(value.replace('Z', '+00:00'))
        if parsed is not None:
            if timezone.is_naive(parsed):
                return timezone.make_aware(parsed)
            return parsed

        parsed_date = parse_date(value)
        if parsed_date is not None:
            return timezone.make_aware(datetime.combine(parsed_date, datetime.min.time()))

    return timezone.now()


def _safe_date(value):
    parsed = parse_date(value) if isinstance(value, str) else value
    if parsed is not None:
        return parsed
    return timezone.now().date()


def _normalize_provider_code(provider_code, provider_name=''):
    raw = provider_code or provider_name or 'custom'
    normalized = re.sub(r'[^a-z0-9]+', '_', str(raw).lower()).strip('_')
    return normalized or 'custom'


def _category_bucket(category_name):
    key = (category_name or 'Uncategorized').strip().lower()
    return CATEGORY_BUCKET_MAP.get(key, 'Operating Expenses')


def _audit_banking_event(integration, user, action, model_name, object_id, changes=None, ip_address=None, entity=None):
    AuditLog.objects.create(
        organization=integration.organization,
        entity=entity or integration.entity,
        user=user,
        action=action,
        model_name=model_name,
        object_id=str(object_id),
        changes=changes or {},
        ip_address=ip_address,
    )


def prepare_oauth_consent(integration, *, redirect_uri, scopes=None, requested_by=None, ip_address=None):
    scopes = scopes or DEFAULT_CONSENT_SCOPES
    provider_code = _normalize_provider_code(integration.provider_code, integration.provider_name)
    state = uuid.uuid4().hex
    authorize_url = os.getenv(f'{provider_code.upper()}_OAUTH_AUTHORIZE_URL', '')
    client_id = decrypt_secret(integration.api_key) or os.getenv(f'{provider_code.upper()}_CLIENT_ID', '')

    consent_log = BankingConsentLog.objects.create(
        organization=integration.organization,
        integration=integration,
        entity=integration.entity,
        user=requested_by,
        provider_code=provider_code,
        status='requested',
        redirect_uri=redirect_uri,
        state=state,
        scopes=scopes,
        ip_address=ip_address,
        metadata={'provider_name': integration.provider_name},
    )

    if authorize_url and client_id and redirect_uri:
        params = {
            'response_type': 'code',
            'client_id': client_id,
            'redirect_uri': redirect_uri,
            'scope': ' '.join(scopes),
            'state': state,
        }
        consent_url = f'{authorize_url}?{urlencode(params)}'
        mode = 'oauth'
    else:
        callback_params = urlencode(
            {
                'bank_integration': integration.id,
                'provider': provider_code,
                'state': state,
                'code': f'demo-{state}',
            }
        )
        separator = '&' if '?' in redirect_uri else '?'
        consent_url = f'{redirect_uri}{separator}{callback_params}'
        mode = 'mock'

    _audit_banking_event(
        integration,
        requested_by,
        'create',
        'BankingConsentLog',
        consent_log.id,
        changes={'status': 'requested', 'provider_code': provider_code, 'scopes': scopes, 'mode': mode},
        ip_address=ip_address,
    )

    return {
        'consent_url': consent_url,
        'consent_mode': mode,
        'state': state,
        'scopes': scopes,
        'consent_log_id': consent_log.id,
    }


def complete_oauth_consent(
    integration,
    *,
    authorization_code,
    state,
    requested_by=None,
    ip_address=None,
    access_token='',
    refresh_token='',
    expires_in=3600,
    consent_reference='',
    metadata=None,
):
    consent_log = (
        integration.consent_logs.filter(state=state)
        .order_by('-requested_at')
        .first()
    )
    if consent_log is None:
        raise ValueError('Invalid or expired consent state.')

    resolved_access_token = access_token or f'{integration.provider_code}-access-{authorization_code}'
    resolved_refresh_token = refresh_token or f'{integration.provider_code}-refresh-{authorization_code}'
    now = timezone.now()

    integration.access_token_encrypted = encrypt_secret(resolved_access_token)
    integration.refresh_token_encrypted = encrypt_secret(resolved_refresh_token)
    integration.token_expires_at = now + timedelta(seconds=int(expires_in or 3600))
    integration.token_last_rotated_at = now
    integration.consent_reference = consent_reference or consent_log.consent_reference or uuid.uuid4().hex[:20]
    integration.consent_scopes = consent_log.scopes or integration.consent_scopes or DEFAULT_CONSENT_SCOPES
    integration.consent_granted_at = now
    integration.consent_revoked_at = None
    integration.consent_metadata = {**integration.consent_metadata, **(metadata or {}), 'authorization_code': authorization_code}
    integration.status = 'active'
    integration.is_active = True
    integration.failure_count = 0
    integration.save()

    consent_log.status = 'granted'
    consent_log.consent_reference = integration.consent_reference
    consent_log.resolved_at = now
    consent_log.metadata = {**consent_log.metadata, **(metadata or {}), 'completed_by': requested_by.id if requested_by else None}
    consent_log.save(update_fields=['status', 'consent_reference', 'resolved_at', 'metadata'])

    _audit_banking_event(
        integration,
        requested_by,
        'update',
        'BankingIntegration',
        integration.id,
        changes={'status': 'active', 'consent_reference': integration.consent_reference},
        ip_address=ip_address,
    )

    return {
        'status': integration.status,
        'consent_reference': integration.consent_reference,
        'token_expires_at': integration.token_expires_at,
    }


def _upsert_bank_account(integration, entity, account_payload):
    provider_account_id = account_payload.get('account_id') or account_payload.get('provider_account_id') or uuid.uuid4().hex
    account_name = account_payload.get('name') or account_payload.get('account_name') or 'Connected Account'
    account_number_masked = account_payload.get('account_number_masked') or account_payload.get('mask') or '****0000'
    bank_name = account_payload.get('bank_name') or account_payload.get('institution_name') or integration.provider_name
    defaults = {
        'account_name': account_name,
        'account_number': account_number_masked,
        'bank_name': bank_name,
        'account_type': account_payload.get('account_type') or 'business',
        'currency': account_payload.get('currency') or entity.local_currency,
        'balance': _safe_decimal(account_payload.get('balance', 0)),
        'available_balance': _safe_decimal(account_payload.get('available_balance', account_payload.get('balance', 0))),
        'is_active': True,
        'last_synced': timezone.now(),
        'verification_status': 'verified' if integration.consent_granted_at else 'pending',
    }
    bank_account, _ = BankAccount.objects.update_or_create(
        entity=entity,
        provider=integration.provider_code,
        provider_account_id=provider_account_id,
        defaults=defaults,
    )
    return bank_account


def _match_rule(rule, merchant_name, description):
    merchant_name = (merchant_name or '').strip()
    description = (description or '').strip()
    merchant_pattern = (rule.merchant_pattern or '').strip()
    description_pattern = (rule.description_pattern or '').strip()

    if rule.match_type == 'exact':
        return bool(
            (merchant_pattern and merchant_name.lower() == merchant_pattern.lower())
            or (description_pattern and description.lower() == description_pattern.lower())
        )

    if rule.match_type == 'regex':
        return bool(
            (merchant_pattern and re.search(merchant_pattern, merchant_name, re.I))
            or (description_pattern and re.search(description_pattern, description, re.I))
        )

    return bool(
        (merchant_pattern and merchant_pattern.lower() in merchant_name.lower())
        or (description_pattern and description_pattern.lower() in description.lower())
    )


def categorize_banking_transaction(banking_transaction, *, user=None, category_name='', dashboard_bucket='', explanation='', source=''):
    merchant_name = banking_transaction.merchant_name or banking_transaction.counterparty_name or ''
    description = banking_transaction.description or ''
    rules = BankingCategorizationRule.objects.filter(entity=banking_transaction.entity, is_active=True).order_by('-priority', 'id')

    selected_rule = None
    assigned_category = category_name.strip()
    resolved_source = source or 'fallback'
    confidence = Decimal('0.35')
    decision_explanation = explanation.strip()

    if not assigned_category:
        for rule in rules:
            if _match_rule(rule, merchant_name, description):
                selected_rule = rule
                assigned_category = rule.category_name
                dashboard_bucket = dashboard_bucket or rule.dashboard_bucket
                resolved_source = 'user_override' if rule.learned_from_user else 'rule_engine'
                confidence = Decimal('0.96') if rule.match_type == 'exact' else Decimal('0.88')
                decision_explanation = decision_explanation or 'Matched a saved merchant or description rule.'
                break

    if not assigned_category and merchant_name:
        merchant_key = merchant_name.strip().lower()
        assigned_category = MERCHANT_CATEGORY_MAP.get(merchant_key, '')
        if assigned_category:
            resolved_source = 'provider_hint'
            confidence = Decimal('0.82')
            decision_explanation = 'Matched a known merchant map.'

    if not assigned_category and banking_transaction.raw_category:
        assigned_category = PROVIDER_HINT_CATEGORY_MAP.get(banking_transaction.raw_category.strip().lower(), '')
        if assigned_category:
            resolved_source = 'provider_hint'
            confidence = Decimal('0.72')
            decision_explanation = 'Used the upstream provider category hint.'

    if not assigned_category:
        for pattern, pattern_category in DESCRIPTION_KEYWORDS:
            if pattern.search(description):
                assigned_category = pattern_category
                resolved_source = 'keyword'
                confidence = Decimal('0.64')
                decision_explanation = 'Matched a keyword rule from the transaction description.'
                break

    if not assigned_category:
        assigned_category = 'Uncategorized'
        resolved_source = source or 'fallback'
        confidence = Decimal('0.25')
        decision_explanation = decision_explanation or 'No matching rule was found.'

    dashboard_bucket = dashboard_bucket or _category_bucket(assigned_category)

    with transaction.atomic():
        banking_transaction.categorization_decisions.filter(is_current=True).update(is_current=False)
        decision = BankingCategorizationDecision.objects.create(
            entity=banking_transaction.entity,
            banking_transaction=banking_transaction,
            matched_rule=selected_rule,
            source=resolved_source,
            raw_category=banking_transaction.raw_category,
            assigned_category=assigned_category,
            dashboard_bucket=dashboard_bucket,
            confidence_score=confidence,
            explanation=decision_explanation,
            created_by=user,
            is_current=True,
        )

        banking_transaction.normalized_category = assigned_category
        banking_transaction.dashboard_bucket = dashboard_bucket
        banking_transaction.categorization_source = resolved_source
        banking_transaction.categorization_confidence = confidence
        banking_transaction.save(
            update_fields=[
                'normalized_category',
                'dashboard_bucket',
                'categorization_source',
                'categorization_confidence',
                'updated_at',
            ]
        )

        if resolved_source == 'user_override' and user and merchant_name:
            BankingCategorizationRule.objects.update_or_create(
                entity=banking_transaction.entity,
                merchant_pattern=merchant_name,
                match_type='exact',
                defaults={
                    'description_pattern': '',
                    'category_name': assigned_category,
                    'dashboard_bucket': dashboard_bucket,
                    'priority': 1000,
                    'learned_from_user': True,
                    'created_by': user,
                    'updated_by': user,
                    'is_active': True,
                },
            )

    integration = banking_transaction.integration
    if integration is not None:
        _audit_banking_event(
            integration,
            user,
            'update',
            'BankingCategorizationDecision',
            decision.id,
            changes={
                'transaction_id': banking_transaction.id,
                'category': assigned_category,
                'bucket': dashboard_bucket,
                'source': resolved_source,
            },
            entity=banking_transaction.entity,
        )

    return decision


def sync_banking_integration(integration, *, payload=None, initiated_by=None, trigger_type='manual'):
    payload = payload or {}
    entity = integration.entity
    entity_id = payload.get('entity') or payload.get('entity_id')
    if entity is None and entity_id:
        entity = Entity.objects.filter(id=entity_id, organization=integration.organization).first()

    if entity is None:
        raise ValueError('A banking integration must be scoped to an entity before transactions can be synced.')

    sync_run = BankingSyncRun.objects.create(
        integration=integration,
        entity=entity,
        initiated_by=initiated_by,
        trigger_type=trigger_type,
        status='running',
        request_payload=payload,
    )

    try:
        accounts_payload = payload.get('accounts') or []
        transactions_payload = payload.get('transactions') or []
        account_lookup = {}

        for account_payload in accounts_payload:
            bank_account = _upsert_bank_account(integration, entity, account_payload)
            account_lookup[bank_account.provider_account_id] = bank_account

        for item in transactions_payload:
            account_id = item.get('account_id') or item.get('provider_account_id')
            bank_account = account_lookup.get(account_id)
            if bank_account is None and account_id:
                bank_account = BankAccount.objects.filter(
                    entity=entity,
                    provider=integration.provider_code,
                    provider_account_id=account_id,
                ).first()
            if bank_account is None:
                bank_account = _upsert_bank_account(
                    integration,
                    entity,
                    {
                        'account_id': account_id or uuid.uuid4().hex,
                        'name': item.get('account_name') or 'Connected Account',
                        'account_type': 'business',
                        'currency': item.get('currency') or entity.local_currency,
                        'balance': item.get('balance', 0),
                    },
                )

            external_id = item.get('external_id') or item.get('transaction_id')
            if not external_id:
                raw_key = f"{bank_account.provider_account_id}:{item.get('date')}:{item.get('amount')}:{item.get('description', '')}"
                external_id = uuid.uuid5(uuid.NAMESPACE_URL, raw_key).hex

            merchant_name = item.get('merchant') or item.get('merchant_name') or item.get('counterparty_name') or ''
            raw_category = item.get('raw_category') or item.get('category') or ''
            amount = _safe_decimal(item.get('amount', 0))
            transaction_defaults = {
                'entity': entity,
                'integration': integration,
                'sync_run': sync_run,
                'bank_account': bank_account,
                'transaction_date': _safe_datetime(item.get('date') or item.get('transaction_date')),
                'amount': amount,
                'currency': item.get('currency') or entity.local_currency,
                'description': item.get('description') or merchant_name or 'Imported transaction',
                'merchant_name': merchant_name,
                'raw_category': raw_category,
                'counterparty_name': item.get('counterparty_name') or merchant_name,
                'counterparty_account': item.get('counterparty_account') or '',
                'transaction_type': item.get('transaction_type') or ('debit' if amount < 0 else 'credit'),
                'status': item.get('status') or 'completed',
                'raw_data': item,
            }
            banking_transaction, _ = BankingTransaction.objects.update_or_create(
                transaction_id=external_id,
                defaults=transaction_defaults,
            )
            categorize_banking_transaction(banking_transaction, user=initiated_by)

        integration.entity = entity
        integration.last_sync = timezone.now()
        integration.failure_count = 0
        integration.status = 'active'
        integration.save(update_fields=['entity', 'last_sync', 'failure_count', 'status', 'updated_at'])

        sync_run.status = 'succeeded'
        sync_run.accounts_processed = len(accounts_payload)
        sync_run.transactions_processed = len(transactions_payload)
        sync_run.completed_at = timezone.now()
        sync_run.response_payload = {
            'message': 'Sync completed successfully.' if transactions_payload or accounts_payload else 'Sync completed with no new upstream records.',
        }
        sync_run.save(
            update_fields=[
                'status',
                'accounts_processed',
                'transactions_processed',
                'completed_at',
                'response_payload',
                'updated_at',
            ]
        )

        _audit_banking_event(
            integration,
            initiated_by,
            'bulk_import',
            'BankingSyncRun',
            sync_run.id,
            changes={
                'trigger_type': trigger_type,
                'accounts_processed': sync_run.accounts_processed,
                'transactions_processed': sync_run.transactions_processed,
            },
            entity=entity,
        )
        return sync_run
    except Exception as exc:
        sync_run.status = 'failed'
        sync_run.error_message = str(exc)
        sync_run.completed_at = timezone.now()
        sync_run.save(update_fields=['status', 'error_message', 'completed_at', 'updated_at'])

        integration.failure_count += 1
        integration.status = 'inactive' if integration.failure_count >= 3 else integration.status
        integration.save(update_fields=['failure_count', 'status', 'updated_at'])
        raise


def handle_banking_webhook(provider_code, payload, signature=''):
    provider_code = _normalize_provider_code(provider_code)
    integration_id = payload.get('integration_id')
    consent_reference = payload.get('consent_reference') or payload.get('item_id')

    integrations = BankingIntegration.objects.filter(provider_code=provider_code, is_active=True)
    if integration_id:
        integrations = integrations.filter(id=integration_id)
    elif consent_reference:
        integrations = integrations.filter(consent_reference=consent_reference)

    processed = []
    for integration in integrations:
        integration.last_webhook_at = timezone.now()
        integration.save(update_fields=['last_webhook_at', 'updated_at'])
        sync_run = sync_banking_integration(
            integration,
            payload=payload,
            initiated_by=None,
            trigger_type='webhook',
        )
        processed.append(sync_run.id)

    return {
        'accepted': bool(processed),
        'processed_sync_runs': processed,
        'signature_present': bool(signature),
    }


def override_banking_transaction_category(banking_transaction, *, category_name, dashboard_bucket='', explanation='', user=None, learn=True):
    decision = categorize_banking_transaction(
        banking_transaction,
        user=user,
        category_name=category_name,
        dashboard_bucket=dashboard_bucket,
        explanation=explanation or 'Category overridden by user action.',
        source='user_override',
    )

    if not learn and user:
        BankingCategorizationRule.objects.filter(
            entity=banking_transaction.entity,
            merchant_pattern=banking_transaction.merchant_name,
            category_name=category_name,
            learned_from_user=True,
        ).delete()

    return decision