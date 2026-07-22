from __future__ import annotations

from django.contrib.auth.models import User
from django.db.models import Prefetch, Q
from django.utils import timezone

from atonixcorp.models import (
    Permission,
    TeamMember,
    EntityStaff,
    ROLE_CFO,
    ROLE_EXTERNAL_ADVISOR,
    ROLE_FINANCE_ANALYST,
    ROLE_ORG_OWNER,
    ROLE_VIEWER,
)
from atonixcorp.models import DashboardAccessGrant

from .models import MemberRole, Workspace, WorkspaceGroup, WorkspaceGroupMember, WorkspaceMember


CATEGORY_KEYS = (
    'finance',
    'accounting',
    'equity',
    'marketing',
    'operations',
    'compliance',
    'audit',
    'voting_decision_rights',
)

LEVEL_NONE = 0
LEVEL_READ = 1
LEVEL_WRITE = 2
LEVEL_MANAGE = 3
LEVEL_DECIDE = 4

LEVEL_LABELS = {
    LEVEL_NONE: 'none',
    LEVEL_READ: 'read',
    LEVEL_WRITE: 'write',
    LEVEL_MANAGE: 'manage',
    LEVEL_DECIDE: 'decide',
}

ORG_ROLE_CATEGORY_LEVELS = {
    ROLE_ORG_OWNER: {
        'finance': LEVEL_DECIDE,
        'accounting': LEVEL_DECIDE,
        'equity': LEVEL_DECIDE,
        'marketing': LEVEL_MANAGE,
        'operations': LEVEL_DECIDE,
        'compliance': LEVEL_DECIDE,
        'audit': LEVEL_DECIDE,
        'voting_decision_rights': LEVEL_DECIDE,
    },
    ROLE_CFO: {
        'finance': LEVEL_DECIDE,
        'accounting': LEVEL_DECIDE,
        'equity': LEVEL_MANAGE,
        'marketing': LEVEL_READ,
        'operations': LEVEL_MANAGE,
        'compliance': LEVEL_DECIDE,
        'audit': LEVEL_DECIDE,
        'voting_decision_rights': LEVEL_DECIDE,
    },
    ROLE_FINANCE_ANALYST: {
        'finance': LEVEL_WRITE,
        'accounting': LEVEL_WRITE,
        'equity': LEVEL_READ,
        'operations': LEVEL_READ,
        'compliance': LEVEL_WRITE,
        'audit': LEVEL_READ,
        'voting_decision_rights': LEVEL_READ,
    },
    ROLE_VIEWER: {
        'finance': LEVEL_READ,
        'accounting': LEVEL_READ,
        'equity': LEVEL_READ,
        'operations': LEVEL_READ,
        'compliance': LEVEL_READ,
        'audit': LEVEL_READ,
    },
    ROLE_EXTERNAL_ADVISOR: {
        'finance': LEVEL_READ,
        'compliance': LEVEL_READ,
        'audit': LEVEL_READ,
    },
}

WORKSPACE_ROLE_CATEGORY_LEVELS = {
    MemberRole.OWNER: {
        'finance': LEVEL_MANAGE,
        'accounting': LEVEL_MANAGE,
        'equity': LEVEL_MANAGE,
        'marketing': LEVEL_MANAGE,
        'operations': LEVEL_DECIDE,
        'compliance': LEVEL_MANAGE,
        'audit': LEVEL_MANAGE,
        'voting_decision_rights': LEVEL_DECIDE,
    },
    MemberRole.ADMIN: {
        'finance': LEVEL_WRITE,
        'accounting': LEVEL_WRITE,
        'equity': LEVEL_WRITE,
        'marketing': LEVEL_MANAGE,
        'operations': LEVEL_MANAGE,
        'compliance': LEVEL_WRITE,
        'audit': LEVEL_WRITE,
        'voting_decision_rights': LEVEL_MANAGE,
    },
    MemberRole.MEMBER: {
        'finance': LEVEL_READ,
        'accounting': LEVEL_READ,
        'equity': LEVEL_READ,
        'marketing': LEVEL_READ,
        'operations': LEVEL_WRITE,
        'compliance': LEVEL_READ,
        'audit': LEVEL_READ,
        'voting_decision_rights': LEVEL_READ,
    },
    MemberRole.VIEWER: {
        'operations': LEVEL_READ,
        'audit': LEVEL_READ,
    },
}

PERMISSION_CATEGORY_LEVELS = {
    'view_org_overview': {'operations': LEVEL_READ, 'finance': LEVEL_READ},
    'manage_org_settings': {'operations': LEVEL_MANAGE, 'voting_decision_rights': LEVEL_MANAGE},
    'manage_billing': {'finance': LEVEL_MANAGE},
    'view_entities': {'finance': LEVEL_READ, 'accounting': LEVEL_READ, 'operations': LEVEL_READ},
    'create_entity': {'operations': LEVEL_MANAGE, 'voting_decision_rights': LEVEL_MANAGE},
    'edit_entity': {'operations': LEVEL_WRITE, 'finance': LEVEL_WRITE},
    'delete_entity': {'operations': LEVEL_DECIDE, 'voting_decision_rights': LEVEL_DECIDE},
    'view_tax_compliance': {'compliance': LEVEL_READ, 'audit': LEVEL_READ},
    'edit_tax_compliance': {'compliance': LEVEL_WRITE},
    'export_tax_reports': {'compliance': LEVEL_MANAGE, 'audit': LEVEL_WRITE},
    'view_cashflow': {'finance': LEVEL_READ, 'accounting': LEVEL_READ},
    'edit_cashflow': {'finance': LEVEL_WRITE, 'accounting': LEVEL_WRITE},
    'view_risk_exposure': {'audit': LEVEL_READ, 'compliance': LEVEL_READ},
    'edit_risk_exposure': {'audit': LEVEL_WRITE, 'compliance': LEVEL_WRITE},
    'view_reports': {'finance': LEVEL_READ, 'accounting': LEVEL_READ, 'audit': LEVEL_READ},
    'generate_reports': {'finance': LEVEL_WRITE, 'accounting': LEVEL_WRITE, 'audit': LEVEL_WRITE},
    'export_reports': {'finance': LEVEL_MANAGE, 'audit': LEVEL_MANAGE},
    'view_team': {'operations': LEVEL_READ},
    'manage_team': {'operations': LEVEL_MANAGE, 'voting_decision_rights': LEVEL_MANAGE},
    'assign_roles': {'operations': LEVEL_MANAGE, 'voting_decision_rights': LEVEL_DECIDE},
}

DEPARTMENT_CATEGORY_LEVELS = {
    'Controllership': {'finance': LEVEL_MANAGE, 'accounting': LEVEL_MANAGE, 'audit': LEVEL_READ},
    'Accounts Payable': {'finance': LEVEL_WRITE, 'accounting': LEVEL_WRITE},
    'Accounts Receivable': {'finance': LEVEL_WRITE, 'accounting': LEVEL_WRITE},
    'Treasury': {'finance': LEVEL_MANAGE, 'accounting': LEVEL_WRITE},
    'Payroll': {'finance': LEVEL_WRITE, 'accounting': LEVEL_WRITE, 'compliance': LEVEL_READ},
    'Tax': {'finance': LEVEL_WRITE, 'compliance': LEVEL_MANAGE, 'audit': LEVEL_WRITE},
    'FP&A': {'finance': LEVEL_MANAGE, 'accounting': LEVEL_READ, 'voting_decision_rights': LEVEL_READ},
    'Financial Reporting': {'finance': LEVEL_MANAGE, 'accounting': LEVEL_MANAGE, 'audit': LEVEL_WRITE},
    'Risk, Audit, and Compliance': {'compliance': LEVEL_DECIDE, 'audit': LEVEL_DECIDE, 'voting_decision_rights': LEVEL_MANAGE},
    'Intercompany and Consolidation': {'finance': LEVEL_MANAGE, 'accounting': LEVEL_MANAGE, 'audit': LEVEL_READ},
    'Marketing': {'marketing': LEVEL_MANAGE, 'operations': LEVEL_WRITE},
    'Operations': {'operations': LEVEL_MANAGE},
    'Finance': {'finance': LEVEL_MANAGE, 'accounting': LEVEL_MANAGE},
    'Equity': {'equity': LEVEL_MANAGE, 'voting_decision_rights': LEVEL_MANAGE},
}

WORKSPACE_SECTION_REQUIREMENTS = {
    'overview': lambda summary: summary['dashboards']['workspace_dashboard'],
    'members': lambda summary: summary['workspace_sections']['members'],
    'departments': lambda summary: summary['workspace_sections']['departments'],
    'meetings': lambda summary: summary['workspace_sections']['meetings'],
    'calendar': lambda summary: summary['workspace_sections']['calendar'],
    'files': lambda summary: summary['workspace_sections']['files'],
    'permissions': lambda summary: summary['workspace_sections']['permissions'],
    'settings': lambda summary: summary['workspace_sections']['settings'],
    'email': lambda summary: summary['workspace_sections']['email'],
    'marketing': lambda summary: summary['workspace_sections']['marketing'],
}


class AccountingPermissionService:
    @staticmethod
    def _empty_levels():
        return {key: LEVEL_NONE for key in CATEGORY_KEYS}

    @staticmethod
    def _escalate(levels, additions):
        if not additions:
            return
        for key, level in additions.items():
            if key in levels:
                levels[key] = max(levels[key], level)

    @staticmethod
    def _serialize_level(level_value):
        return {
            'level': LEVEL_LABELS[level_value],
            'read': level_value >= LEVEL_READ,
            'write': level_value >= LEVEL_WRITE,
            'manage': level_value >= LEVEL_MANAGE,
            'decide': level_value >= LEVEL_DECIDE,
        }

    @staticmethod
    def _enabled_workspace_modules(workspace):
        if workspace.linked_entity and isinstance(workspace.linked_entity.enabled_modules, list):
            return list(workspace.linked_entity.enabled_modules)
        return list(workspace.modules.values_list('module_key', flat=True))

    @staticmethod
    def _department_levels_for_names(names):
        levels = AccountingPermissionService._empty_levels()
        for name in names:
            AccountingPermissionService._escalate(levels, DEPARTMENT_CATEGORY_LEVELS.get(name, {}))
        return levels

    @staticmethod
    def _entity_staff_department_names(entity_staff):
        names = []
        if entity_staff and entity_staff.department and entity_staff.department.name:
            names.append(entity_staff.department.name)
        return names

    @staticmethod
    def _workspace_department_names(workspace_departments, actor):
        names = []
        for department in workspace_departments:
            if department.owner_id == actor.id:
                names.append(department.name)
                continue
            if any(member.user_id == actor.id for member in department.group_members.all()):
                names.append(department.name)
        return names

    @staticmethod
    def _permission_codes_for_member(team_member, is_org_owner):
        if is_org_owner:
            return list(Permission.objects.values_list('code', flat=True))
        if not team_member or not team_member.role_id:
            return []
        return list(team_member.role.permissions.values_list('code', flat=True))

    @staticmethod
    def get_permission_summary(workspace_id, user: User):
        workspace = Workspace.objects.select_related('linked_entity__organization').prefetch_related(
            'modules',
            Prefetch(
                'groups',
                queryset=WorkspaceGroup.objects.select_related('owner').prefetch_related(
                    Prefetch('group_members', queryset=WorkspaceGroupMember.objects.select_related('user'))
                ),
            ),
        ).get(pk=workspace_id)

        membership = WorkspaceMember.objects.filter(workspace_id=workspace_id, user=user).first()
        workspace_grant = None
        if membership is None:
            workspace_grant = DashboardAccessGrant.objects.select_related('invitation').filter(
                workspace_id=workspace_id,
                user=user,
                branch=DashboardAccessGrant.BRANCH_WORKSPACE,
                revoked_at__isnull=True,
            ).filter(
                Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now()),
                Q(invitation__isnull=True) | Q(invitation__is_active=True, invitation__accepted_at__isnull=False),
            ).first()
            if workspace_grant is None:
                return None

        effective_role = membership.role if membership is not None else MemberRole.VIEWER
        if membership is None and workspace_grant is None:
            return None

        organization = getattr(workspace.linked_entity, 'organization', None)
        is_org_owner = bool(organization and organization.owner_id == user.id)
        team_member = None
        if organization and not is_org_owner:
            team_member = TeamMember.objects.select_related('role').prefetch_related('role__permissions', 'scoped_entities').filter(
                organization=organization,
                user=user,
                is_active=True,
            ).first()

        entity_staff = None
        if workspace.linked_entity_id:
            entity_staff = EntityStaff.objects.select_related('role', 'department').prefetch_related('role__permissions').filter(
                entity_id=workspace.linked_entity_id,
                user=user,
                status='active',
            ).first()

        org_role_code = ROLE_ORG_OWNER if is_org_owner else getattr(getattr(team_member, 'role', None), 'code', None)
        org_role_name = 'Organization Owner' if is_org_owner else getattr(getattr(team_member, 'role', None), 'name', None)
        entity_role = getattr(entity_staff, 'role', None)
        entity_role_code = getattr(entity_role, 'code', None)
        entity_role_name = getattr(entity_role, 'name', None)
        entity_role_permission_codes = list(entity_role.permissions.values_list('code', flat=True)) if entity_role else []
        permission_codes = AccountingPermissionService._permission_codes_for_member(team_member, is_org_owner)

        levels = AccountingPermissionService._empty_levels()
        AccountingPermissionService._escalate(levels, ORG_ROLE_CATEGORY_LEVELS.get(org_role_code, {}))
        AccountingPermissionService._escalate(levels, WORKSPACE_ROLE_CATEGORY_LEVELS.get(effective_role, {}))

        for permission_code in permission_codes + entity_role_permission_codes:
            AccountingPermissionService._escalate(levels, PERMISSION_CATEGORY_LEVELS.get(permission_code, {}))

        workspace_departments = list(workspace.groups.all())
        entity_department_names = AccountingPermissionService._entity_staff_department_names(entity_staff)
        workspace_department_names = AccountingPermissionService._workspace_department_names(workspace_departments, user)
        all_department_names = entity_department_names + workspace_department_names
        AccountingPermissionService._escalate(levels, AccountingPermissionService._department_levels_for_names(all_department_names))

        department_owner_ids = [department.id for department in workspace_departments if department.owner_id == user.id]

        enabled_modules = AccountingPermissionService._enabled_workspace_modules(workspace)
        has_equity = any(module_key.startswith('equity_') for module_key in enabled_modules) or getattr(workspace.linked_entity, 'workspace_mode', '') in {'equity', 'combined', 'standalone'}
        has_accounting = any(not module_key.startswith('equity_') for module_key in enabled_modules) or getattr(workspace.linked_entity, 'workspace_mode', '') in {'accounting', 'combined'}

        if has_equity and effective_role != MemberRole.VIEWER:
            levels['equity'] = max(levels['equity'], LEVEL_WRITE)
        elif has_equity:
            levels['equity'] = max(levels['equity'], LEVEL_READ)

        can_manage_members = effective_role in {MemberRole.OWNER, MemberRole.ADMIN} or levels['operations'] >= LEVEL_MANAGE
        can_manage_departments = effective_role in {MemberRole.OWNER, MemberRole.ADMIN}
        can_manage_owned_departments = bool(department_owner_ids)
        can_manage_settings = effective_role in {MemberRole.OWNER, MemberRole.ADMIN} or levels['finance'] >= LEVEL_MANAGE
        can_delete_workspace = effective_role == MemberRole.OWNER or is_org_owner

        can_see_all_departments = can_manage_departments or org_role_code in {ROLE_ORG_OWNER, ROLE_CFO} or levels['audit'] >= LEVEL_MANAGE
        visible_departments = []
        for department in workspace_departments:
            is_owner = department.owner_id == user.id
            is_member = any(member.user_id == user.id for member in department.group_members.all())
            department_matches_entity = department.name in entity_department_names
            can_access = can_see_all_departments or is_owner or is_member or department_matches_entity
            if can_access:
                visible_departments.append({
                    'id': str(department.id),
                    'name': department.name,
                    'cost_center': department.cost_center,
                    'description': department.description,
                    'is_owner': is_owner,
                    'is_member': is_member,
                    'can_manage': can_manage_departments or is_owner,
                })

        visible_department_ids = [item['id'] for item in visible_departments]

        workspace_sections = {
            'overview': True,
            'members': effective_role != MemberRole.VIEWER or can_manage_members,
            'departments': bool(visible_departments) or can_manage_departments,
            'meetings': effective_role != MemberRole.VIEWER,
            'calendar': effective_role != MemberRole.VIEWER,
            'files': effective_role != MemberRole.VIEWER,
            'permissions': can_manage_members or levels['audit'] >= LEVEL_READ or levels['voting_decision_rights'] >= LEVEL_READ,
            'settings': can_manage_settings,
            'email': effective_role != MemberRole.VIEWER,
            'marketing': levels['marketing'] >= LEVEL_READ or effective_role in {MemberRole.OWNER, MemberRole.ADMIN},
        }

        equity_sections = {
            'me': has_equity and levels['equity'] >= LEVEL_READ,
            'registry': has_equity and 'equity_registry' in enabled_modules and levels['equity'] >= LEVEL_READ,
            'cap-table': has_equity and 'equity_cap_table' in enabled_modules and levels['equity'] >= LEVEL_READ,
            'grants': has_equity and 'equity_vesting' in enabled_modules and levels['equity'] >= LEVEL_READ,
            'exercises': has_equity and 'equity_exercises' in enabled_modules and levels['equity'] >= LEVEL_READ,
            'automation': has_equity and levels['equity'] >= LEVEL_WRITE,
            'valuation': has_equity and 'equity_valuation' in enabled_modules and levels['equity'] >= LEVEL_READ,
            'approvals': has_equity and levels['voting_decision_rights'] >= LEVEL_READ,
            'scenarios': has_equity and levels['equity'] >= LEVEL_WRITE,
            'transactions': has_equity and 'equity_transactions' in enabled_modules and levels['equity'] >= LEVEL_WRITE,
            'governance': has_equity and 'equity_governance' in enabled_modules and levels['audit'] >= LEVEL_READ,
        }

        actions = {
            'read': True,
            'write': effective_role != MemberRole.VIEWER,
            'manage_members': can_manage_members,
            'manage_departments': can_manage_departments,
            'manage_owned_departments': can_manage_owned_departments,
            'manage_meetings': effective_role != MemberRole.VIEWER,
            'manage_files': effective_role != MemberRole.VIEWER,
            'manage_settings': can_manage_settings,
            'manage_modules': can_manage_settings,
            'delete_workspace': can_delete_workspace,
            'change_tier': can_delete_workspace,
            'change_status': can_delete_workspace,
        }

        return {
            'workspace_id': str(workspace.id),
            'user_id': user.pk,
            'workspace_role': effective_role,
            'context': {
                'organization_id': organization.id if organization else None,
                'organization_role_code': org_role_code,
                'organization_role_name': org_role_name,
                'entity_id': workspace.linked_entity_id,
                'entity_role_code': entity_role_code,
                'entity_role_name': entity_role_name,
                'entity_department_names': entity_department_names,
                'workspace_department_names': workspace_department_names,
                'permission_codes': sorted(set(permission_codes + entity_role_permission_codes)),
                'scoped_entity_ids': list(team_member.scoped_entities.values_list('id', flat=True)) if team_member else [],
                'module_keys': enabled_modules,
                'has_accounting_workspace': has_accounting,
                'has_equity_workspace': has_equity,
            },
            'categories': {
                key: AccountingPermissionService._serialize_level(levels[key])
                for key in CATEGORY_KEYS
            },
            'actions': actions,
            'dashboards': {
                'workspace_dashboard': workspace_sections['overview'],
                'entity_dashboard': bool(workspace.linked_entity_id and (levels['finance'] >= LEVEL_READ or levels['accounting'] >= LEVEL_READ or levels['compliance'] >= LEVEL_READ)),
                'project_dashboard': effective_role != MemberRole.VIEWER or levels['compliance'] >= LEVEL_READ,
                'equity_dashboard': any(equity_sections.values()),
            },
            'workspace_sections': workspace_sections,
            'equity_sections': equity_sections,
            'visible_departments': visible_departments,
            'visible_department_ids': visible_department_ids,
        }

    @staticmethod
    def can_access_workspace_section(summary, section_key):
        resolver = WORKSPACE_SECTION_REQUIREMENTS.get(section_key)
        if resolver is None:
            return False
        return bool(resolver(summary))