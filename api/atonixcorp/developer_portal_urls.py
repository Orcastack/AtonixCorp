from django.urls import path

from .developer_portal_views import (
    DeveloperAPIDetailView,
    DeveloperAPIEndpointDetailView,
    DeveloperAPIEndpointListView,
    DeveloperAPIListView,
    DeveloperAuthenticationDocsView,
    DeveloperErrorsDocsView,
    DeveloperKeyRequestView,
    DeveloperSearchView,
    DeveloperStatusView,
)


urlpatterns = [
    path('apis', DeveloperAPIListView.as_view(), name='developer-api-list'),
    path('apis/<slug:slug>', DeveloperAPIDetailView.as_view(), name='developer-api-detail'),
    path('apis/<slug:slug>/endpoints', DeveloperAPIEndpointListView.as_view(), name='developer-api-endpoints'),
    path('apis/<slug:slug>/endpoints/<int:endpoint_id>', DeveloperAPIEndpointDetailView.as_view(), name='developer-api-endpoint-detail'),
    path('search', DeveloperSearchView.as_view(), name='developer-search'),
    path('docs/authentication', DeveloperAuthenticationDocsView.as_view(), name='developer-docs-authentication'),
    path('docs/errors', DeveloperErrorsDocsView.as_view(), name='developer-docs-errors'),
    path('status', DeveloperStatusView.as_view(), name='developer-status'),
    path('keys/request', DeveloperKeyRequestView.as_view(), name='developer-key-request'),
]