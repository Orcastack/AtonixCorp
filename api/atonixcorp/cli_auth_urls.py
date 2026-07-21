from django.urls import path

from .cli_auth_views import CLIAuthLoginView, CLIAuthMeView, CLIAuthRefreshView


urlpatterns = [
    path('cli-login', CLIAuthLoginView.as_view(), name='cli-auth-login'),
    path('refresh', CLIAuthRefreshView.as_view(), name='cli-auth-refresh'),
    path('me', CLIAuthMeView.as_view(), name='cli-auth-me'),
]