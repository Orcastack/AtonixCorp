from rest_framework.throttling import SimpleRateThrottle


class _TaxOrganizationScopedThrottle(SimpleRateThrottle):
    def _scope_ident(self, request):
        request_data = getattr(request, 'data', {}) or {}
        entity_id = request.query_params.get('entity_id') or request_data.get('entity_id')
        if entity_id:
            return f'entity:{entity_id}'

        organization_id = request.headers.get('X-Organization-Id') or request.META.get('HTTP_X_ORGANIZATION_ID')
        if organization_id:
            return f'org:{organization_id.strip().lower()}'

        user = getattr(request, 'user', None)
        if user and getattr(user, 'is_authenticated', False):
            return f'user:{user.pk}'

        return self.get_ident(request)


class TaxApiBurstThrottle(_TaxOrganizationScopedThrottle):
    scope = 'tax_api_burst'

    def get_cache_key(self, request, view):
        ident = f"{self._scope_ident(request)}:{request.method}:{request.path}"
        return self.cache_format % {'scope': self.scope, 'ident': ident}


class TaxApiWriteThrottle(_TaxOrganizationScopedThrottle):
    scope = 'tax_api_write'

    def get_cache_key(self, request, view):
        ident = f"{self._scope_ident(request)}:{request.method}:{request.path}"
        return self.cache_format % {'scope': self.scope, 'ident': ident}
