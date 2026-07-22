from django.urls import path

from .auth_views import (
    IdentityVerificationView,
    MeView,
    RegisterView,
    ResendEmailVerificationView,
    SecureUserIdTokenObtainPairSerializer,
    UsernameSuggestionsView,
    VerifyEmailView,
)
from .developer_portal_common import StandardizedTokenObtainPairView, StandardizedTokenRefreshView


urlpatterns = [
    path("register/", RegisterView.as_view(), name="auth_register"),
    path("username-suggestions/", UsernameSuggestionsView.as_view(), name="auth_username_suggestions"),
    path("token/", StandardizedTokenObtainPairView.as_view(serializer_class=SecureUserIdTokenObtainPairSerializer), name="token_obtain_pair"),
    path("token/refresh/", StandardizedTokenRefreshView.as_view(), name="token_refresh"),
    path("me/", MeView.as_view(), name="auth_me"),
    path("verify-email/", VerifyEmailView.as_view(), name="verify_email"),
    path("resend-verification/", ResendEmailVerificationView.as_view(), name="resend_email_verification"),
    path("identity-verification/", IdentityVerificationView.as_view(), name="identity_verification"),
]
