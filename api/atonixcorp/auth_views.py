import logging
import re

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
logger = logging.getLogger(__name__)


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
        'identity_code': getattr(profile, 'identity_code', ''),
        'public_user_id': getattr(profile, 'public_user_id', ''),
        'platform_role': getattr(profile, 'platform_role', UserProfile.PLATFORM_ROLE_MEMBER),
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

        profile = UserProfile.objects.select_related('user').filter(public_user_id__iexact=raw_value).first()
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
            raise AuthenticationFailed('Please verify your email first. Request a new verification link to continue.')
        data['user'] = _user_payload(self.user)
        return data


class RegisterView(DeveloperFacingAPIView):
    permission_classes = [AllowAny]

    def post(self, request):
        payload = request.data or {}
        email = (payload.get("email") or "").strip().lower()
        username = (payload.get("username") or "").strip()
        first_name = (payload.get("first_name") or "").strip()
        last_name = (payload.get("last_name") or "").strip()
        password = payload.get("password") or ""
        account_type = (payload.get("account_type") or ACCOUNT_TYPE_ENTERPRISE).strip()
        country = (payload.get("country") or "").strip()
        phone = (payload.get("phone") or "").strip()
        tax_type = (payload.get("tax_type") or "").strip() or None
        tax_rate = payload.get("tax_rate")

        if not email:
            return Response({"email": "This field is required."}, status=status.HTTP_400_BAD_REQUEST)
        if not username:
            return Response({"username": "This field is required."}, status=status.HTTP_400_BAD_REQUEST)
        if not first_name:
            return Response({"first_name": "This field is required."}, status=status.HTTP_400_BAD_REQUEST)
        if username.casefold() == email.casefold():
            return Response({"username": "Username or employee ID must be different from your email address."}, status=status.HTTP_400_BAD_REQUEST)
        if len(username) > User._meta.get_field('username').max_length:
            return Response({"username": "Username must be 150 characters or fewer."}, status=status.HTTP_400_BAD_REQUEST)
        if not password:
            return Response({"password": "This field is required."}, status=status.HTTP_400_BAD_REQUEST)
        existing_user = User.objects.filter(email__iexact=email).first()
        if existing_user:
            existing_profile = getattr(existing_user, 'profile', None)
            if not existing_profile or not existing_profile.email_verified:
                return Response(
                    {
                        'email': 'An account with this email already exists and needs verification.',
                        'verification_required': True,
                    },
                    status=status.HTTP_409_CONFLICT,
                )
            return Response(
                {"email": "An account with this email already exists. Sign in with your email, username, or employee ID."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if User.objects.filter(username__iexact=username).exists():
            return Response({"username": "This username is already in use."}, status=status.HTTP_400_BAD_REQUEST)

        is_first_user = not User.objects.exists()
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
        )
        if is_first_user:
            user.is_staff = True
            user.is_superuser = True
            user.save(update_fields=['is_staff', 'is_superuser'])

        # Create profile so the frontend starts from real stored values (no mock).
        profile = UserProfile.objects.create(
            user=user,
            account_type=account_type if account_type in [ACCOUNT_TYPE_PERSONAL, ACCOUNT_TYPE_ENTERPRISE] else ACCOUNT_TYPE_ENTERPRISE,
            country=country,
            phone=phone,
            platform_role=UserProfile.PLATFORM_ROLE_SUPER_USER if is_first_user else UserProfile.PLATFORM_ROLE_MEMBER,
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

        verification_email_sent = True
        verification_email_error = None
        try:
            send_verification_email(user)
        except Exception:
            verification_email_sent = False
            verification_email_error = 'Account created. The verification email could not be sent right now. You can request a new verification link after sign-in or contact support.'
            logger.exception('Unable to send verification email for newly registered user %s', user.pk)
        return Response(
            {
                "user": _user_payload(user),
                "verification_required": True,
                "verification_email_sent": verification_email_sent,
                "detail": verification_email_error,
            },
            status=status.HTTP_201_CREATED,
        )


class UsernameSuggestionsView(DeveloperFacingAPIView):
    permission_classes = [AllowAny]

    def get(self, request):
        scope = str(request.query_params.get('scope') or 'user').strip().lower()
        raw_name = str(request.query_params.get('name') or request.query_params.get('first_name') or '').strip()
        base = re.sub(r'[^a-z0-9]', '', raw_name.lower())[:140]
        if not base:
            raise ValidationError({'name': 'A first name or enterprise name is required.'})

        year = timezone.localdate().year
        candidates = [f'{base}01', f'{base}{year}', f'{base}_global']
        if scope == 'enterprise':
            from .models import Organization

            available = [candidate for candidate in candidates if not Organization.objects.filter(enterprise_username__iexact=candidate).exists()]
        elif scope == 'user':
            available = [candidate for candidate in candidates if not User.objects.filter(username__iexact=candidate).exists()]
        else:
            raise ValidationError({'scope': 'Scope must be user or enterprise.'})
        return Response({'suggestions': available or candidates, 'scope': scope})


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
        identifier = str((request.data or {}).get('email') or '').strip()
        username = SecureUserIdTokenObtainPairSerializer._resolve_username(identifier)
        user = User.objects.filter(username__iexact=username).first()
        profile = getattr(user, 'profile', None) if user else None
        if user and profile and not profile.email_verified:
            try:
                send_verification_email(user)
            except Exception:
                logger.exception('Unable to resend verification email for user %s', user.pk)
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
