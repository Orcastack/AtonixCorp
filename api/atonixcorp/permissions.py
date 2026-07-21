"""
Permission checking utilities and decorators for enterprise features
"""
from functools import wraps
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from django.http import JsonResponse
from .models import TeamMember, Organization, Role, ROLE_ORG_OWNER, ROLE_CFO, ROLE_COMPLIANCE_OFFICER


class PermissionChecker:
    """Utility for checking user permissions against roles"""

    @staticmethod
    def user_has_permission(user, organization, permission_code):
        """
        Check if a user has a specific permission in an organization
        
        Args:
            user: Django User object
            organization: Organization object
            permission_code: Permission code string (e.g., 'view_org_overview')
        
        Returns:
            Boolean indicating if user has permission
        """
        if not user.is_authenticated:
            return False

        # Organization owner always has all permissions
        if organization.owner == user:
            return True

        # Check team membership and role permissions
        try:
            team_member = TeamMember.objects.select_related('role').get(
                organization=organization,
                user=user,
                is_active=True
            )
            return team_member.role.permissions.filter(code=permission_code).exists()
        except TeamMember.DoesNotExist:
            return False

    @staticmethod
    def user_has_role(user, organization, role_code):
        """Check if user has a specific role"""
        if organization.owner == user:
            return role_code == ROLE_ORG_OWNER

        try:
            team_member = TeamMember.objects.select_related('role').get(
                organization=organization,
                user=user,
                is_active=True
            )
            return team_member.role.code == role_code
        except TeamMember.DoesNotExist:
            return False

    @staticmethod
    def user_can_access_entity(user, organization, entity):
        """Check if user can access a specific entity"""
        if organization.owner == user:
            return True

        try:
            team_member = TeamMember.objects.get(
                organization=organization,
                user=user,
                is_active=True
            )
            # External advisor has scoped access
            if team_member.scoped_entities.exists():
                return team_member.scoped_entities.filter(id=entity.id).exists()
            # Others with entity access can see all
            return True
        except TeamMember.DoesNotExist:
            return False

    @staticmethod
    def user_role_hierarchy(user, organization):
        """Get the hierarchy level of user's role (higher = more access)"""
        if organization.owner == user:
            return 5  # Owner

        try:
            team_member = TeamMember.objects.select_related('role').get(
                organization=organization,
                user=user,
                is_active=True
            )
            role_hierarchy = {
                ROLE_ORG_OWNER: 5,
                ROLE_CFO: 4,
                ROLE_COMPLIANCE_OFFICER: 4,
                'FINANCE_ANALYST': 3,
                'VIEWER': 2,
                'EXTERNAL_ADVISOR': 1,
            }
            return role_hierarchy.get(team_member.role.code, 0)
        except TeamMember.DoesNotExist:
            return 0


def require_permission(permission_code):
    """
    Decorator to check permission on a view
    
    Usage:
        @require_permission('view_org_overview')
        def my_view(request, *args, **kwargs):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Get organization from kwargs or query params
            org_id = kwargs.get('organization_id') or request.query_params.get('organization_id')
            if not org_id:
                return Response({'error': 'Organization ID required'}, status=400)

            try:
                organization = Organization.objects.get(id=org_id)
            except Organization.DoesNotExist:
                return Response({'error': 'Organization not found'}, status=404)

            # Check permission
            if not PermissionChecker.user_has_permission(request.user, organization, permission_code):
                raise PermissionDenied(f"User does not have '{permission_code}' permission")

            # Add organization to request for use in view
            request.organization = organization
            return view_func(request, *args, **kwargs)

        return wrapper
    return decorator


def require_role(role_code):
    """
    Decorator to check if user has a specific role
    
    Usage:
        @require_role('CFO')
        def my_view(request, *args, **kwargs):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            org_id = kwargs.get('organization_id') or request.query_params.get('organization_id')
            if not org_id:
                return Response({'error': 'Organization ID required'}, status=400)

            try:
                organization = Organization.objects.get(id=org_id)
            except Organization.DoesNotExist:
                return Response({'error': 'Organization not found'}, status=404)

            if not PermissionChecker.user_has_role(request.user, organization, role_code):
                raise PermissionDenied(f"User does not have '{role_code}' role")

            request.organization = organization
            return view_func(request, *args, **kwargs)

        return wrapper
    return decorator


def require_organization_access(view_func):
    """
    Decorator to ensure user is part of organization or is owner
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        org_id = kwargs.get('organization_id') or request.query_params.get('organization_id')
        if not org_id:
            return Response({'error': 'Organization ID required'}, status=400)

        try:
            organization = Organization.objects.get(id=org_id)
        except Organization.DoesNotExist:
            return Response({'error': 'Organization not found'}, status=404)

        # Check if user is owner or team member
        if organization.owner != request.user:
            try:
                TeamMember.objects.get(
                    organization=organization,
                    user=request.user,
                    is_active=True
                )
            except TeamMember.DoesNotExist:
                raise PermissionDenied("User does not have access to this organization")

        request.organization = organization
        return view_func(request, *args, **kwargs)

    return wrapper
