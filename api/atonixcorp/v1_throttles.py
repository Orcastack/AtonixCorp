from rest_framework.throttling import SimpleRateThrottle


class _OrganizationScopedThrottle(SimpleRateThrottle):
    def _scope_ident(self, request):
        organization = getattr(request, '_v1_organization', None)
        if organization is not None:
            return f'org:{organization.pk}'

        header_value = request.headers.get('X-Organization-Id') or request.META.get('HTTP_X_ORGANIZATION_ID')
        if header_value:
            return f'org:{header_value.strip().lower()}'

        user = getattr(request, 'user', None)
        if user and getattr(user, 'is_authenticated', False):
            return f'user:{user.pk}'

        return self.get_ident(request)


class V1OrganizationBurstThrottle(_OrganizationScopedThrottle):
    scope = 'v1_org_burst'

    def get_cache_key(self, request, view):
        ident = self._scope_ident(request)
        return self.cache_format % {'scope': self.scope, 'ident': ident}


class V1OrganizationEndpointThrottle(_OrganizationScopedThrottle):
    scope = 'v1_endpoint'

    def get_cache_key(self, request, view):
        ident = f"{self._scope_ident(request)}:{request.method}:{request.path}"
        return self.cache_format % {'scope': self.scope, 'ident': ident}