from rest_framework.permissions import BasePermission
from rest_framework.exceptions import PermissionDenied

from .models import APIKey


V1_API_KEY_SCOPE_POLICY = {
    'v1-api-keys': {'GET': ['auth:manage'], 'POST': ['auth:manage']},
    'v1-api-key-rotate': {'POST': ['auth:manage']},
    'v1-api-key-revoke': {'POST': ['auth:manage']},
    'v1-organizations': {'GET': ['org:read'], 'POST': ['org:write']},
    'v1-roles': {'GET': ['team:read']},
    'v1-permissions': {'GET': ['team:read']},
    'v1-team-members': {'GET': ['team:read'], 'POST': ['team:write']},
    'v1-team-member-invitations': {'POST': ['team:write']},
    'v1-team-member-deactivate': {'POST': ['team:write']},
    'v1-migration-jobs': {'GET': ['migration:read'], 'POST': ['migration:write']},
    'v1-migration-job-detail': {'GET': ['migration:read']},
    'v1-migration-bank-statements': {'POST': ['migration:write', 'banking:write']},
    'v1-migration-chart-of-accounts': {'POST': ['migration:write']},
    'v1-migration-customers': {'POST': ['migration:write']},
    'v1-migration-historical-financials': {'POST': ['migration:write', 'ledger:write']},
    'v1-migration-vendors': {'POST': ['migration:write']},
    'v1-migration-invoices': {'POST': ['migration:write']},
    'v1-migration-bills': {'POST': ['migration:write']},
    'v1-migration-transactions': {'POST': ['migration:write']},
    'v1-migration-opening-balances': {'POST': ['migration:write']},
    'v1-accounts': {'GET': ['accounts:read'], 'POST': ['accounts:write']},
    'v1-customers': {'GET': ['customers:read'], 'POST': ['customers:write']},
    'v1-vendors': {'GET': ['vendors:read'], 'POST': ['vendors:write']},
    'v1-bills': {'GET': ['bills:read'], 'POST': ['bills:write']},
    'v1-bill-payments': {'POST': ['payments:write']},
    'v1-journal-entries': {'GET': ['ledger:read'], 'POST': ['ledger:write']},
    'v1-invoices': {'POST': ['invoices:write']},
    'v1-invoice-payments': {'POST': ['payments:write']},
    'v1-bank-accounts': {'GET': ['banking:read'], 'POST': ['banking:write']},
    'v1-bank-account-transactions': {'GET': ['banking:read'], 'POST': ['banking:write']},
    'v1-reconciliation-matches': {'GET': ['banking:read'], 'POST': ['banking:write']},
    'v1-trial-balance': {'GET': ['reports:read']},
    'v1-profit-and-loss': {'GET': ['reports:read']},
    'v1-balance-sheet': {'GET': ['reports:read']},
    'v1-cash-flow': {'GET': ['reports:read']},
    'v1-system-events': {'GET': ['audit:read']},
    'v1-webhook-endpoints': {'GET': ['webhooks:read'], 'POST': ['webhooks:write']},
    'v1-webhook-deliveries': {'GET': ['webhooks:read']},
    'v1-webhook-event-replay': {'POST': ['webhooks:write']},
}


class APIKeyScopePermission(BasePermission):
    message = 'Insufficient API key scope.'

    def has_permission(self, request, view):
        auth = getattr(request, 'auth', None)
        if not isinstance(auth, APIKey):
            return True

        resolver_match = getattr(request, 'resolver_match', None)
        url_name = getattr(resolver_match, 'url_name', None)
        required_scopes = (V1_API_KEY_SCOPE_POLICY.get(url_name) or {}).get(request.method, [])
        if not required_scopes:
            return True

        granted_scopes = set(auth.scopes or [])
        if '*' in granted_scopes:
            return True
        if all(scope in granted_scopes for scope in required_scopes):
            return True

        raise PermissionDenied(
            detail=f'Missing required API scope(s): {", ".join(required_scopes)}',
            code='insufficient_scope',
        )