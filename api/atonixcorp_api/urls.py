"""
URL configuration for the AtonixCorp API project.
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from atonixcorp.developer_portal_views import (
    DeveloperAPIDetailView,
    DeveloperAPIEndpointDetailView,
    DeveloperAPIEndpointListView,
    DeveloperAPIListView,
    DeveloperKeyRequestView,
    DeveloperSearchView,
    DeveloperStatusView,
)
from atonixcorp.views import landing_page

urlpatterns = [
    path(
        'favicon.ico',
        RedirectView.as_view(url=f'{settings.STATIC_URL}branding/atc-logo-round.svg', permanent=False),
    ),
    path('admin/', admin.site.urls),
    path('auth/', include('atonixcorp.cli_auth_urls')),
    path('developer/', include('atonixcorp.developer_portal_urls')),
    path('apis', DeveloperAPIListView.as_view(), name='public-api-list'),
    path('apis/<slug:slug>', DeveloperAPIDetailView.as_view(), name='public-api-detail'),
    path('apis/<slug:slug>/endpoints', DeveloperAPIEndpointListView.as_view(), name='public-api-endpoints'),
    path('apis/<slug:slug>/endpoints/<int:endpoint_id>', DeveloperAPIEndpointDetailView.as_view(), name='public-api-endpoint-detail'),
    path('search', DeveloperSearchView.as_view(), name='public-api-search'),
    path('keys/register', DeveloperKeyRequestView.as_view(), name='public-key-register'),
    path('docs/apis', DeveloperAPIListView.as_view(), name='public-api-docs'),
    path('docs/apis/<slug:slug>', DeveloperAPIDetailView.as_view(), name='public-api-docs-detail'),
    path('status', DeveloperStatusView.as_view(), name='public-status'),
    path('v1/', include('atonixcorp.v1_urls')),
    path('api/', include('atonixcorp.urls')),
    path('api/', include('equity.urls')),
    path('api/auth/', include('atonixcorp.auth_urls')),
    path('api/v1/', include('workspaces.urls')),
    path('api/v1/', include('intelligence.urls')),
    path('', landing_page, name='landing_page'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
