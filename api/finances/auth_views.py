from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied, ValidationError
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from rest_framework_simplejwt.tokens import RefreshToken

from .developer_portal_common import DeveloperFacingAPIView
from .email_verification import send_verification_email, verify_email_token
from .models import IdentityVerification, UserProfile, ACCOUNT_TYPE_ENTERPRISE, ACCOUNT_TYPE_PERSONAL
from .organization_email_service import send_system_notification


User = get_user_model()


def _registration_username(email):
    """Generate a unique internal username while keeping email as the login identity."""
    max_length = User._meta.get_field('username').max_length
    base = email[:max_length]
    candidate = base
    suffix = 1
    while User.objects.filter(username__iexact=candidate).exists():
        suffix += 1
        suffix_text = f'-{suffix}'
        candidate = f'{base[:max_length - len(suffix_text)]}{suffix_text}'
    return candidate


def _user_payload(user):
    profile = getattr(user, 'profile', None)
    return {
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'account_type': getattr(profile, 'account_type', ACCOUNT_TYPE_PERSONAL),
        'country': getattr(profile, 'country', ''),
        'phone': getattr(profile, 'phone', ''),
        'tax_type': getattr(profile, 'tax_type', UserProfile.TAX_TYPE_CORPORATE),
        'tax_rate': float(getattr(profile, 'tax_rate', 0) or 0),
        'secure_user_id': getattr(profile, 'secure_user_id', ''),
        'email_verified': bool(getattr(profile, 'email_verified', False)),
    }


class SecureUserIdTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def _resolve_username(cls, submitted_username):
        raw_value = (submitted_username or '').strip()
        if not raw_value:
            return raw_value

        if raw_value.isdigit() and len(raw_value) == 10:
            profile = UserProfile.objects.select_related('user').filter(secure_user_id=raw_value).first()
            if profile:
                return profile.user.get_username()

        user = User.objects.filter(email__iexact=raw_value).first()
        if user:
            return user.get_username()

        return raw_value

    def validate(self, attrs):
        attrs = attrs.copy()
        attrs[self.username_field] = self._resolve_username(attrs.get(self.username_field))
        data = super().validate(attrs)

        profile = getattr(self.user, 'profile', None)
        if not profile or not profile.email_verified:
            send_verification_email(self.user)
            raise AuthenticationFailed('Please verify your email first. A new verification link has been sent.')
        data['user'] = _user_payload(self.user)
        return data


class RegisterView(DeveloperFacingAPIView):
    permission_classes = [AllowAny]

    def post(self, request):
        payload = request.data or {}
        email = (payload.get("email") or "").strip().lower()
        username = (payload.get("username") or "").strip()
        password = payload.get("password") or ""
        account_type = (payload.get("account_type") or ACCOUNT_TYPE_ENTERPRISE).strip()
        country = (payload.get("country") or "").strip()
        phone = (payload.get("phone") or "").strip()
        tax_type = (payload.get("tax_type") or "").strip() or None
        tax_rate = payload.get("tax_rate")

        if not email:
            return Response({"email": "This field is required."}, status=status.HTTP_400_BAD_REQUEST)
        if not password:
            return Response({"password": "This field is required."}, status=status.HTTP_400_BAD_REQUEST)
        if User.objects.filter(email__iexact=email).exists():
            return Response({"email": "A user with this email already exists."}, status=status.HTTP_400_BAD_REQUEST)
        if username and User.objects.filter(username__iexact=username).exists():
            return Response({"username": "This username is already in use."}, status=status.HTTP_400_BAD_REQUEST)

        username = username or _registration_username(email)
        user = User.objects.create_user(username=username, email=email, password=password)

        # Create profile so the frontend starts from real stored values (no mock).
        profile = UserProfile.objects.create(
            user=user,
            account_type=account_type if account_type in [ACCOUNT_TYPE_PERSONAL, ACCOUNT_TYPE_ENTERPRISE] else ACCOUNT_TYPE_ENTERPRISE,
            country=country,
            phone=phone,
        )

        if tax_type in [UserProfile.TAX_TYPE_CORPORATE, UserProfile.TAX_TYPE_PERSONAL, UserProfile.TAX_TYPE_VAT]:
            profile.tax_type = tax_type

        if tax_rate is not None and tax_rate != "":
            try:
                profile.tax_rate = float(tax_rate)
            except (TypeError, ValueError):
                pass
        profile.save(update_fields=['tax_type', 'tax_rate', 'updated_at'])

        send_system_notification(
            recipient=user.email,
            subject='Welcome to AtonixCorp',
            title='Welcome to AtonixCorp',
            message='Your account is ready. Verify your email address, then sign in to create your organization workspace.',
            event_type='account_registration',
        )

        send_verification_email(user)
        return Response(
            {
                "user": _user_payload(user),
                "verification_required": True,
            },
            status=status.HTTP_201_CREATED,
        )


class MeView(DeveloperFacingAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        profile = getattr(user, 'profile', None)
        if not profile or not profile.email_verified:
            raise PermissionDenied('Please verify your email first.')
        return Response(_user_payload(user))

    def patch(self, request):
        user = request.user
        profile = getattr(user, 'profile', None)
        payload = request.data or {}

        if payload.get('first_name') is not None:
            user.first_name = str(payload.get('first_name') or '').strip()
        if payload.get('last_name') is not None:
            user.last_name = str(payload.get('last_name') or '').strip()
        user.save(update_fields=['first_name', 'last_name'])

        if profile is None:
            profile = UserProfile.objects.create(user=user)

        if payload.get('country') is not None:
            profile.country = str(payload.get('country') or '').strip()
        if payload.get('phone') is not None:
            profile.phone = str(payload.get('phone') or '').strip()

        tax_type = payload.get('tax_type')
        if tax_type in [UserProfile.TAX_TYPE_CORPORATE, UserProfile.TAX_TYPE_PERSONAL, UserProfile.TAX_TYPE_VAT]:
            profile.tax_type = tax_type

        if payload.get('tax_rate') is not None and payload.get('tax_rate') != '':
            try:
                profile.tax_rate = float(payload.get('tax_rate'))
            except (TypeError, ValueError):
                return Response({"tax_rate": "Must be a number."}, status=status.HTTP_400_BAD_REQUEST)

        profile.save()
        return self.get(request)


class VerifyEmailView(DeveloperFacingAPIView):
    permission_classes = [AllowAny]

    def get(self, request):
        token = request.query_params.get('token', '')
        if not token:
            raise ValidationError({'token': 'A verification token is required.'})
        user = verify_email_token(token)
        refresh = RefreshToken.for_user(user)
        identity = getattr(user, 'identity_verification', None)
        next_path = '/app/console' if identity and identity.status == IdentityVerification.STATUS_VERIFIED else '/app/verification'
        return Response({
            'user': _user_payload(user),
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'next_path': next_path,
        })


class ResendEmailVerificationView(DeveloperFacingAPIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = str((request.data or {}).get('email') or '').strip().lower()
        user = User.objects.filter(email__iexact=email).first()
        if user and not getattr(user.profile, 'email_verified', False):
            send_verification_email(user)
        return Response({'detail': 'If this account requires verification, a new link has been sent.'})


class IdentityVerificationView(DeveloperFacingAPIView):
    permission_classes = [IsAuthenticated]

    def _verification(self, user):
        return IdentityVerification.objects.get_or_create(user=user)[0]

    def get(self, request):
        verification = self._verification(request.user)
        return Response({
            'status': verification.status,
            'id_document_uploaded': bool(verification.id_document),
            'selfie_uploaded': bool(verification.selfie),
            'rejection_reason': verification.rejection_reason,
        })

    def post(self, request):
        profile = getattr(request.user, 'profile', None)
        if not profile or not profile.email_verified:
            raise PermissionDenied('Please verify your email first.')
        id_document = request.FILES.get('id_document')
        selfie = request.FILES.get('selfie')
        if not id_document or not selfie:
            raise ValidationError({'detail': 'Upload both an ID document and a selfie.'})
        verification = self._verification(request.user)
        verification.id_document = id_document
        verification.selfie = selfie
        verification.status = IdentityVerification.STATUS_SUBMITTED
        verification.submitted_at = timezone.now()
        verification.rejection_reason = ''
        verification.save()
        return self.get(request)
