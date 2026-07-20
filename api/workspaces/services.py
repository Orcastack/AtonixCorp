"""
Workspace services — all business logic.
Every service enforces membership + role before mutating data.
Every write generates a WorkspaceLog entry via LogService.
Selected workspace activity is mirrored into the shared platform audit stream.
"""
import secrets
import base64
import hashlib
from io import BytesIO
from django.apps import apps
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import transaction
from django.db.models import Count, Q
from django.contrib.auth.models import User
from rest_framework.exceptions import PermissionDenied, NotFound, ValidationError

from .models import (
    DEFAULT_MODULES,
    MemberRole,
    ParticipantStatus,
    Workspace, WorkspaceStatus, WorkspaceTier,
    WorkspaceCalendarEvent,
    WorkspaceFile, WorkspaceFolder,
    WorkspaceGroup, WorkspaceGroupMember,
    WorkspaceLog,
    WorkspaceMeeting, WorkspaceMeetingParticipant,
    WorkspaceMember,
    WorkspaceModule,
    WorkspaceSetting,
)
from .accounting_permissions import AccountingPermissionService
from .type_registry import get_workspace_type_definition


FINANCE_DEPARTMENT_TEMPLATES = [
    {
        'name': 'Controllership',
        'description': 'Owns accounting policy, chart of accounts governance, journal oversight, and close quality.',
        'cost_center': 'FIN-CTRL-100',
    },
    {
        'name': 'Accounts Payable',
        'description': 'Runs supplier operations, invoice workflows, payment approvals, and outbound obligations.',
        'cost_center': 'FIN-AP-110',
    },
    {
        'name': 'Accounts Receivable',
        'description': 'Manages customer billing, collections, receivables aging, and cash application.',
        'cost_center': 'FIN-AR-120',
    },
    {
        'name': 'Treasury',
        'description': 'Handles cash positioning, liquidity planning, banking operations, and payment execution.',
        'cost_center': 'FIN-TRSY-130',
    },
    {
        'name': 'Payroll',
        'description': 'Coordinates payroll operations, pay runs, banking outputs, and payroll-linked obligations.',
        'cost_center': 'FIN-PAY-140',
    },
    {
        'name': 'Tax',
        'description': 'Oversees tax calculations, monitoring, filings, deadlines, and cross-jurisdiction compliance.',
        'cost_center': 'FIN-TAX-150',
    },
    {
        'name': 'FP&A',
        'description': 'Drives budgeting, forecasting, planning cycles, management targets, and variance analysis.',
        'cost_center': 'FIN-FPA-160',
    },
    {
        'name': 'Financial Reporting',
        'description': 'Produces statements, management packs, analytics, board reporting, and formal financial outputs.',
        'cost_center': 'FIN-REP-170',
    },
    {
        'name': 'Risk, Audit, and Compliance',
        'description': 'Owns audit readiness, compliance controls, risk visibility, approvals, and close governance.',
        'cost_center': 'FIN-RISK-180',
    },
    {
        'name': 'Intercompany and Consolidation',
        'description': 'Coordinates intercompany operations, eliminations, consolidation control, and multi-entity reporting.',
        'cost_center': 'FIN-CONS-190',
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# 3.7  PermissionService  (used by every other service)
# ─────────────────────────────────────────────────────────────────────────────

class PermissionService:
    """Role resolution and permission enforcement for workspace operations."""

    # Actions permitted per role (cumulative upwards)
    _ROLE_WEIGHT = {
        MemberRole.VIEWER: 0,
        MemberRole.MEMBER: 1,
        MemberRole.ADMIN:  2,
        MemberRole.OWNER:  3,
    }

    # Minimum role required for each action category
    _ACTION_MIN_ROLE = {
        'read':            MemberRole.VIEWER,
        'write':           MemberRole.MEMBER,
        'manage_members':  MemberRole.ADMIN,
        'manage_groups':   MemberRole.ADMIN,
        'manage_meetings': MemberRole.MEMBER,
        'manage_files':    MemberRole.MEMBER,
        'manage_settings': MemberRole.ADMIN,
        'manage_modules':  MemberRole.ADMIN,
        'delete_workspace':MemberRole.OWNER,
        'change_tier':     MemberRole.OWNER,
        'change_status':   MemberRole.OWNER,
    }

    @staticmethod
    def get_role(workspace_id, user) -> str | None:
        """Return the user's role in the workspace, or None if not a member."""
        try:
            membership = WorkspaceMember.objects.get(
                workspace_id=workspace_id, user=user
            )
            return membership.role
        except WorkspaceMember.DoesNotExist:
            return None

    @classmethod
    def assert_member(cls, workspace_id, user):
        """Raise PermissionDenied if user is not a member."""
        role = cls.get_role(workspace_id, user)
        if role is None:
            raise PermissionDenied('You are not a member of this workspace.')
        return role

    @classmethod
    def assert_permission(cls, workspace_id, user, action: str):
        """
        Assert that the user has sufficient role for `action`.
        Raises PermissionDenied with a clear message on failure.
        """
        role = cls.assert_member(workspace_id, user)
        summary = AccountingPermissionService.get_permission_summary(workspace_id, user)
        if not summary:
            raise PermissionDenied('You are not a member of this workspace.')

        if not summary['actions'].get(action, False):
            min_role = cls._ACTION_MIN_ROLE.get(action, MemberRole.OWNER)
            raise PermissionDenied(
                f'Action "{action}" requires accounting access equivalent to "{min_role}" or higher. '
                f'Your workspace role is "{role}".'
            )
        return role

    @staticmethod
    def get_permission_summary(workspace_id, user):
        return AccountingPermissionService.get_permission_summary(workspace_id, user)

    @staticmethod
    def assert_workspace_section(workspace_id, user, section_key):
        summary = AccountingPermissionService.get_permission_summary(workspace_id, user)
        if not summary:
            raise PermissionDenied('You are not a member of this workspace.')
        if not AccountingPermissionService.can_access_workspace_section(summary, section_key):
            raise PermissionDenied(f'Accounting access does not permit the "{section_key}" workspace section.')
        return summary

    @classmethod
    def assert_owner_or_admin(cls, workspace_id, user):
        cls.assert_permission(workspace_id, user, 'manage_members')

    @classmethod
    def assert_owner(cls, workspace_id, user):
        cls.assert_permission(workspace_id, user, 'delete_workspace')


# ─────────────────────────────────────────────────────────────────────────────
# 3.9  LogService
# ─────────────────────────────────────────────────────────────────────────────

class LogService:
    @staticmethod
    def log(workspace_id, actor, action: str, metadata: dict = None):
        metadata = metadata or {}
        WorkspaceLog.objects.create(
            workspace_id=workspace_id,
            actor=actor,
            action=action,
            metadata=metadata,
        )
        from finances.platform_foundation import log_workspace_activity_as_platform_event

        log_workspace_activity_as_platform_event(
            workspace_id=workspace_id,
            actor=actor,
            action=action,
            metadata=metadata,
        )


# ─────────────────────────────────────────────────────────────────────────────
# 3.1  WorkspaceService
# ─────────────────────────────────────────────────────────────────────────────

class WorkspaceService:

    @staticmethod
    def ensure_workspace_for_entity(entity):
        workspace = Workspace.objects.filter(linked_entity=entity).first()
        if workspace:
            return workspace
        return WorkspaceService.create_workspace(
            entity.organization.owner,
            {
                'name': entity.name,
                'description': f'Collaboration workspace for {entity.name}',
                'linked_entity_id': entity.id,
            },
        )

    @staticmethod
    def resolve_workspace_id(workspace_ref):
        if isinstance(workspace_ref, Workspace):
            return workspace_ref.pk

        try:
            return Workspace.objects.only('id').get(pk=workspace_ref).pk
        except (Workspace.DoesNotExist, ValueError, TypeError):
            pass

        ref_value = str(workspace_ref).strip()
        if ref_value.isdigit():
            Entity = apps.get_model('finances', 'Entity')
            try:
                entity = Entity.objects.select_related('organization').get(pk=int(ref_value))
            except Entity.DoesNotExist:
                raise NotFound('Workspace not found.')
            return WorkspaceService.ensure_workspace_for_entity(entity).pk

        raise NotFound('Workspace not found.')

    @staticmethod
    def _resolve_linked_entity(linked_entity_id, *, current_workspace_id=None):
        if linked_entity_id in (None, ''):
            return None
        Entity = apps.get_model('finances', 'Entity')
        try:
            entity = Entity.objects.select_related('organization').get(pk=linked_entity_id)
        except Entity.DoesNotExist:
            raise ValidationError({'linked_entity_id': 'Linked entity not found.'})
        linked_workspace_qs = Workspace.objects.filter(linked_entity_id=linked_entity_id)
        if current_workspace_id:
            linked_workspace_qs = linked_workspace_qs.exclude(pk=current_workspace_id)
        if linked_workspace_qs.exists():
            raise ValidationError({'linked_entity_id': 'This entity is already linked to another workspace.'})
        return entity

    @staticmethod
    def _seed_default_departments(workspace: Workspace):
        linked_entity = getattr(workspace, 'linked_entity', None)
        hierarchy_metadata = getattr(linked_entity, 'hierarchy_metadata', {}) or {}
        selected_branch = hierarchy_metadata.get('selected_branch_label') or hierarchy_metadata.get('selected_branch')
        selected_sub_branch = hierarchy_metadata.get('selected_sub_branch_label') or hierarchy_metadata.get('selected_sub_branch')
        available_branches = hierarchy_metadata.get('available_branches') or []

        templates = []
        if selected_branch:
            templates.append({
                'name': selected_branch,
                'description': f'{selected_branch} branch for {workspace.name}',
                'cost_center': f'OPS-{selected_branch[:6].upper()}',
            })

        matching_branch = None
        for branch in available_branches:
            if branch.get('label') == selected_branch or branch.get('key') == selected_branch:
                matching_branch = branch
                break

        if selected_sub_branch:
            templates.append({
                'name': selected_sub_branch,
                'description': f'{selected_sub_branch} team for {workspace.name}',
                'cost_center': f'OPS-{selected_sub_branch[:6].upper()}',
            })

        if matching_branch:
            for child in matching_branch.get('children', []):
                if child == selected_sub_branch:
                    continue
                templates.append({
                    'name': child,
                    'description': f'{child} function within {matching_branch.get("label")}',
                    'cost_center': f'OPS-{child[:6].upper()}',
                })

        manual_departments = [item.strip() for item in str(hierarchy_metadata.get('departments_text') or '').split(',') if item.strip()]
        for department_name in manual_departments:
            templates.append({
                'name': department_name,
                'description': f'{department_name} department',
                'cost_center': f'OPS-{department_name[:6].upper()}',
            })

        if not templates:
            templates = FINANCE_DEPARTMENT_TEMPLATES

        deduped_templates = []
        seen_names = set()
        for template in templates:
            if template['name'] in seen_names:
                continue
            seen_names.add(template['name'])
            deduped_templates.append(template)

        WorkspaceGroup.objects.bulk_create([
            WorkspaceGroup(
                workspace=workspace,
                name=template['name'],
                description=template['description'],
                owner=workspace.owner,
                cost_center=template['cost_center'],
            )
            for template in deduped_templates
        ])

    @staticmethod
    def _workspace_module_keys(linked_entity):
        enabled_modules = getattr(linked_entity, 'enabled_modules', None)
        if isinstance(enabled_modules, list) and enabled_modules:
            return enabled_modules

        workspace_type_definition = get_workspace_type_definition(getattr(linked_entity, 'workspace_type', '')) if linked_entity else None
        if workspace_type_definition:
            return workspace_type_definition['modules']

        return DEFAULT_MODULES

    @staticmethod
    @transaction.atomic
    def create_workspace(user: User, payload: dict) -> Workspace:
        """Create workspace, seed modules, insert owner member, log."""
        name = payload.get('name', '').strip()
        if not name:
            raise ValidationError({'name': 'Workspace name is required.'})
        linked_entity = WorkspaceService._resolve_linked_entity(payload.get('linked_entity_id'))

        ws = Workspace.objects.create(
            owner=user,
            linked_entity=linked_entity,
            name=name,
            description=payload.get('description', ''),
            tier=payload.get('tier', WorkspaceTier.FREE),
        )

        # Seed default modules
        WorkspaceModule.objects.bulk_create([
            WorkspaceModule(workspace=ws, module_key=key, enabled=True)
            for key in WorkspaceService._workspace_module_keys(linked_entity)
        ])

        # Owner is automatically a member with role=owner
        existing_codes = set(WorkspaceMember.objects.values_list('member_code', flat=True))
        member_code = None
        while member_code is None or member_code in existing_codes:
            member_code = f'{secrets.randbelow(1_000_000):06d}'
        WorkspaceMember.objects.create(workspace=ws, user=user, role=MemberRole.OWNER, status=ParticipantStatus.ACCEPTED, member_code=member_code)

        WorkspaceService._seed_default_departments(ws)

        LogService.log(ws.id, user, 'workspace.created', {'name': ws.name})
        return ws

    @staticmethod
    def get_workspace(workspace_id, user: User) -> Workspace:
        """Return workspace if user is a member."""
        try:
            ws = Workspace.objects.get(pk=workspace_id)
        except Workspace.DoesNotExist:
            raise NotFound('Workspace not found.')
        PermissionService.assert_member(workspace_id, user)
        return ws

    @staticmethod
    @transaction.atomic
    def update_workspace(workspace_id, user: User, payload: dict) -> Workspace:
        PermissionService.assert_owner_or_admin(workspace_id, user)
        try:
            ws = Workspace.objects.get(pk=workspace_id)
        except Workspace.DoesNotExist:
            raise NotFound('Workspace not found.')

        if 'linked_entity_id' in payload:
            ws.linked_entity = WorkspaceService._resolve_linked_entity(
                payload.get('linked_entity_id'),
                current_workspace_id=ws.pk,
            )

        allowed = ('name', 'description')
        for field in allowed:
            if field in payload:
                setattr(ws, field, payload[field])
        ws.save()
        LogService.log(workspace_id, user, 'workspace.updated', payload)
        return ws

    @staticmethod
    @transaction.atomic
    def change_tier(workspace_id, user: User, tier: str) -> Workspace:
        PermissionService.assert_owner(workspace_id, user)
        if tier not in WorkspaceTier.values:
            raise ValidationError({'tier': f'Invalid tier "{tier}".'})
        ws = Workspace.objects.get(pk=workspace_id)
        ws.tier = tier
        ws.save()
        LogService.log(workspace_id, user, 'workspace.tier_changed', {'tier': tier})
        return ws

    @staticmethod
    @transaction.atomic
    def change_status(workspace_id, user: User, status: str) -> Workspace:
        PermissionService.assert_owner(workspace_id, user)
        if status not in WorkspaceStatus.values:
            raise ValidationError({'status': f'Invalid status "{status}".'})
        ws = Workspace.objects.get(pk=workspace_id)
        ws.status = status
        ws.save()
        LogService.log(workspace_id, user, 'workspace.status_changed', {'status': status})
        return ws

    @staticmethod
    def list_user_workspaces(user: User):
        """Return all workspaces where the user holds any membership."""
        member_ws_ids = WorkspaceMember.objects.filter(user=user).values_list('workspace_id', flat=True)
        return Workspace.objects.filter(pk__in=member_ws_ids).exclude(status=WorkspaceStatus.DELETED).select_related('linked_entity__organization').annotate(
            members_count=Count('members', distinct=True),
            departments_count=Count('groups', distinct=True),
            clients_count=Count('linked_entity__organization__clients', distinct=True),
            component_count=Count('modules', filter=Q(modules__enabled=True), distinct=True),
        )


# ─────────────────────────────────────────────────────────────────────────────
# 3.2  MemberService
# ─────────────────────────────────────────────────────────────────────────────

class MemberService:

    @staticmethod
    def _generate_member_code():
        return f'{secrets.randbelow(1_000_000):06d}'

    @staticmethod
    def _assign_member_code(member: WorkspaceMember):
        if member.member_code:
            return member.member_code

        while True:
            candidate = MemberService._generate_member_code()
            if not WorkspaceMember.objects.filter(member_code=candidate).exists():
                member.member_code = candidate
                return candidate

    @staticmethod
    @transaction.atomic
    def add_member(workspace_id, actor: User, user: User, role: str) -> WorkspaceMember:
        PermissionService.assert_owner_or_admin(workspace_id, actor)
        if role not in MemberRole.values:
            raise ValidationError({'role': f'Invalid role "{role}".'})
        if role == MemberRole.OWNER:
            raise PermissionDenied('Cannot assign owner role via this endpoint.')
        member, created = WorkspaceMember.objects.get_or_create(
            workspace_id=workspace_id,
            user=user,
            defaults={'role': role, 'status': ParticipantStatus.ACCEPTED, 'member_code': MemberService._generate_member_code()},
        )
        if not created:
            if member.status == ParticipantStatus.INVITED and member.role is None:
                member.role = role
                member.status = ParticipantStatus.ACCEPTED
                MemberService._assign_member_code(member)
                member.save(update_fields=['role', 'status', 'member_code'])
                LogService.log(workspace_id, actor, 'member.invite_accepted', {'user_id': str(user.pk), 'role': role})
                return member
            raise ValidationError({'user': 'User is already a member of this workspace.'})
        MemberService._assign_member_code(member)
        member.save(update_fields=['member_code'])
        LogService.log(workspace_id, actor, 'member.added', {'user_id': str(user.pk), 'role': role})
        return member

    @staticmethod
    @transaction.atomic
    def invite_member(workspace_id, actor: User, user: User) -> WorkspaceMember:
        PermissionService.assert_owner_or_admin(workspace_id, actor)
        member, created = WorkspaceMember.objects.get_or_create(
            workspace_id=workspace_id,
            user=user,
            defaults={'role': None, 'status': ParticipantStatus.INVITED, 'member_code': MemberService._generate_member_code()},
        )
        if not created:
            if member.role is not None and member.status == ParticipantStatus.ACCEPTED:
                raise ValidationError({'user': 'User is already a member of this workspace.'})
            member.role = None
            member.status = ParticipantStatus.INVITED
            MemberService._assign_member_code(member)
            member.save(update_fields=['role', 'status', 'member_code'])
        LogService.log(workspace_id, actor, 'member.invited', {'user_id': str(user.pk)})
        return member

    @staticmethod
    @transaction.atomic
    def remove_member(workspace_id, actor: User, user: User):
        PermissionService.assert_owner_or_admin(workspace_id, actor)
        try:
            membership = WorkspaceMember.objects.get(workspace_id=workspace_id, user=user)
        except WorkspaceMember.DoesNotExist:
            raise NotFound('Member not found.')
        if membership.role == MemberRole.OWNER:
            raise PermissionDenied('Cannot remove the workspace owner.')
        membership.delete()
        # Remove from all departments in this workspace
        WorkspaceGroupMember.objects.filter(
            group__workspace_id=workspace_id, user=user
        ).delete()
        LogService.log(workspace_id, actor, 'member.removed', {'user_id': str(user.pk)})

    @staticmethod
    @transaction.atomic
    def update_role(workspace_id, actor: User, user: User, role: str) -> WorkspaceMember:
        PermissionService.assert_owner_or_admin(workspace_id, actor)
        if role not in MemberRole.values:
            raise ValidationError({'role': f'Invalid role "{role}".'})
        if role == MemberRole.OWNER:
            raise PermissionDenied('Cannot assign owner role via this endpoint.')
        try:
            membership = WorkspaceMember.objects.get(workspace_id=workspace_id, user=user)
        except WorkspaceMember.DoesNotExist:
            raise NotFound('Member not found.')
        if membership.role == MemberRole.OWNER:
            raise PermissionDenied('Cannot change the role of the workspace owner.')
        membership.role = role
        membership.save()
        LogService.log(workspace_id, actor, 'member.role_changed', {'user_id': str(user.pk), 'role': role})
        return membership

    @staticmethod
    def list_members(workspace_id, actor: User):
        PermissionService.assert_member(workspace_id, actor)
        return WorkspaceMember.objects.filter(workspace_id=workspace_id).select_related('user')

    @staticmethod
    def member_department_map(workspace_id):
        department_map = {}
        memberships = WorkspaceGroupMember.objects.filter(
            group__workspace_id=workspace_id,
        ).select_related('group', 'user').order_by('group__name')

        for membership in memberships:
            department_map.setdefault(membership.user_id, []).append(membership.group.name)

        return department_map


# ─────────────────────────────────────────────────────────────────────────────
# 3.3  DepartmentService
# ─────────────────────────────────────────────────────────────────────────────

class DepartmentService:

    @staticmethod
    def _validate_owner(workspace_id, owner_user_id):
        if owner_user_id in (None, ''):
            return None
        try:
            membership = WorkspaceMember.objects.select_related('user').get(
                workspace_id=workspace_id,
                user_id=owner_user_id,
            )
        except WorkspaceMember.DoesNotExist:
            raise ValidationError({'owner_user_id': 'Department owner must already be a member of this workspace.'})
        return membership.user

    @staticmethod
    @transaction.atomic
    def create_department(workspace_id, actor: User, payload: dict) -> WorkspaceGroup:
        PermissionService.assert_owner_or_admin(workspace_id, actor)
        name = payload.get('name', '').strip()
        if not name:
            raise ValidationError({'name': 'Department name is required.'})
        if WorkspaceGroup.objects.filter(workspace_id=workspace_id, name=name).exists():
            raise ValidationError({'name': 'A department with this name already exists.'})
        owner = DepartmentService._validate_owner(workspace_id, payload.get('owner_user_id'))
        department = WorkspaceGroup.objects.create(
            workspace_id=workspace_id,
            name=name,
            description=payload.get('description', ''),
            owner=owner,
            cost_center=(payload.get('cost_center') or '').strip(),
        )
        LogService.log(
            workspace_id,
            actor,
            'department.created',
            {
                'department_id': str(department.pk),
                'name': name,
                'owner_user_id': str(owner.pk) if owner else None,
                'cost_center': department.cost_center,
            },
        )
        return department

    @staticmethod
    @transaction.atomic
    def update_department(workspace_id, actor: User, department_id, payload: dict) -> WorkspaceGroup:
        PermissionService.assert_owner_or_admin(workspace_id, actor)
        try:
            department = WorkspaceGroup.objects.get(pk=department_id, workspace_id=workspace_id)
        except WorkspaceGroup.DoesNotExist:
            raise NotFound('Department not found.')

        updates = {}
        if 'name' in payload:
            name = payload.get('name', '').strip()
            if not name:
                raise ValidationError({'name': 'Department name is required.'})
            if WorkspaceGroup.objects.filter(workspace_id=workspace_id, name=name).exclude(pk=department.pk).exists():
                raise ValidationError({'name': 'A department with this name already exists.'})
            department.name = name
            updates['name'] = name

        if 'description' in payload:
            department.description = payload.get('description', '')
            updates['description'] = department.description

        if 'owner_user_id' in payload:
            owner = DepartmentService._validate_owner(workspace_id, payload.get('owner_user_id'))
            department.owner = owner
            updates['owner_user_id'] = str(owner.pk) if owner else None

        if 'cost_center' in payload:
            department.cost_center = (payload.get('cost_center') or '').strip()
            updates['cost_center'] = department.cost_center

        if updates:
            department.save()
            LogService.log(workspace_id, actor, 'department.updated', {'department_id': str(department.pk), **updates})
        return department

    @staticmethod
    @transaction.atomic
    def delete_department(workspace_id, actor: User, department_id):
        PermissionService.assert_owner_or_admin(workspace_id, actor)
        try:
            department = WorkspaceGroup.objects.get(pk=department_id, workspace_id=workspace_id)
        except WorkspaceGroup.DoesNotExist:
            raise NotFound('Department not found.')
        department_name = department.name
        department.delete()
        LogService.log(workspace_id, actor, 'department.deleted', {'department_id': str(department_id), 'name': department_name})

    @staticmethod
    @transaction.atomic
    def add_member(workspace_id, actor: User, department_id, user: User) -> WorkspaceGroupMember:
        PermissionService.assert_owner_or_admin(workspace_id, actor)
        try:
            department = WorkspaceGroup.objects.get(pk=department_id, workspace_id=workspace_id)
        except WorkspaceGroup.DoesNotExist:
            raise NotFound('Department not found.')
        # User must be a workspace member
        if not WorkspaceMember.objects.filter(workspace_id=workspace_id, user=user).exists():
            raise ValidationError({'user': 'User is not a member of this workspace.'})
        gm, created = WorkspaceGroupMember.objects.get_or_create(group=department, user=user)
        if not created:
            raise ValidationError({'user': 'User is already in this department.'})
        LogService.log(workspace_id, actor, 'department.member_added', {'department_id': str(department.pk), 'user_id': str(user.pk)})
        return gm

    @staticmethod
    @transaction.atomic
    def remove_member(workspace_id, actor: User, department_id, user: User):
        PermissionService.assert_owner_or_admin(workspace_id, actor)
        deleted, _ = WorkspaceGroupMember.objects.filter(
            group__pk=department_id, group__workspace_id=workspace_id, user=user
        ).delete()
        if not deleted:
            raise NotFound('Department member not found.')
        LogService.log(workspace_id, actor, 'department.member_removed', {'department_id': str(department_id), 'user_id': str(user.pk)})

    @staticmethod
    def list_departments(workspace_id, actor: User):
        summary = PermissionService.assert_workspace_section(workspace_id, actor, 'departments')
        queryset = WorkspaceGroup.objects.filter(workspace_id=workspace_id).select_related('owner').prefetch_related('group_members__user')
        if summary['actions'].get('manage_departments'):
            return queryset
        return queryset.filter(pk__in=summary['visible_department_ids'])


class GroupService(DepartmentService):
    create_group = DepartmentService.create_department
    update_group = DepartmentService.update_department
    delete_group = DepartmentService.delete_department
    list_groups = DepartmentService.list_departments


# ─────────────────────────────────────────────────────────────────────────────
# 3.4  MeetingService
# ─────────────────────────────────────────────────────────────────────────────

class MeetingService:

    @staticmethod
    @transaction.atomic
    def create_meeting(workspace_id, actor: User, payload: dict) -> WorkspaceMeeting:
        PermissionService.assert_permission(workspace_id, actor, 'manage_meetings')
        title = payload.get('title', '').strip()
        if not title:
            raise ValidationError({'title': 'Meeting title is required.'})
        start_at = payload.get('start_at')
        end_at   = payload.get('end_at')
        if not start_at or not end_at:
            raise ValidationError({'start_at': 'start_at and end_at are required.'})
        meeting = WorkspaceMeeting.objects.create(
            workspace_id=workspace_id,
            title=title,
            description=payload.get('description', ''),
            start_at=start_at,
            end_at=end_at,
            created_by=actor,
        )
        # Creator is auto-accepted participant
        WorkspaceMeetingParticipant.objects.create(meeting=meeting, user=actor, status='accepted')
        LogService.log(workspace_id, actor, 'meeting.created', {'meeting_id': str(meeting.pk), 'title': title})
        return meeting

    @staticmethod
    @transaction.atomic
    def update_meeting(workspace_id, actor: User, meeting_id, payload: dict) -> WorkspaceMeeting:
        PermissionService.assert_permission(workspace_id, actor, 'manage_meetings')
        try:
            meeting = WorkspaceMeeting.objects.get(pk=meeting_id, workspace_id=workspace_id)
        except WorkspaceMeeting.DoesNotExist:
            raise NotFound('Meeting not found.')
        for field in ('title', 'description', 'start_at', 'end_at'):
            if field in payload:
                setattr(meeting, field, payload[field])
        meeting.save()
        LogService.log(workspace_id, actor, 'meeting.updated', {'meeting_id': str(meeting.pk)})
        return meeting

    @staticmethod
    @transaction.atomic
    def cancel_meeting(workspace_id, actor: User, meeting_id):
        PermissionService.assert_permission(workspace_id, actor, 'manage_meetings')
        try:
            meeting = WorkspaceMeeting.objects.get(pk=meeting_id, workspace_id=workspace_id)
        except WorkspaceMeeting.DoesNotExist:
            raise NotFound('Meeting not found.')
        meeting.delete()
        LogService.log(workspace_id, actor, 'meeting.cancelled', {'meeting_id': str(meeting_id)})

    @staticmethod
    def list_meetings(workspace_id, actor: User):
        PermissionService.assert_member(workspace_id, actor)
        return WorkspaceMeeting.objects.filter(workspace_id=workspace_id).prefetch_related('participants')


# ─────────────────────────────────────────────────────────────────────────────
# 3.5  CalendarService
# ─────────────────────────────────────────────────────────────────────────────

class CalendarService:

    @staticmethod
    @transaction.atomic
    def create_event(workspace_id, actor: User, payload: dict) -> WorkspaceCalendarEvent:
        PermissionService.assert_permission(workspace_id, actor, 'write')
        title = payload.get('title', '').strip()
        if not title:
            raise ValidationError({'title': 'Event title is required.'})
        event = WorkspaceCalendarEvent.objects.create(
            workspace_id=workspace_id,
            title=title,
            description=payload.get('description', ''),
            start_at=payload['start_at'],
            end_at=payload['end_at'],
            type=payload.get('type', 'custom'),
            created_by=actor,
        )
        LogService.log(workspace_id, actor, 'calendar.event_created', {'event_id': str(event.pk)})
        return event

    @staticmethod
    @transaction.atomic
    def update_event(workspace_id, actor: User, event_id, payload: dict) -> WorkspaceCalendarEvent:
        PermissionService.assert_permission(workspace_id, actor, 'write')
        try:
            event = WorkspaceCalendarEvent.objects.get(pk=event_id, workspace_id=workspace_id)
        except WorkspaceCalendarEvent.DoesNotExist:
            raise NotFound('Event not found.')
        for field in ('title', 'description', 'start_at', 'end_at', 'type'):
            if field in payload:
                setattr(event, field, payload[field])
        event.save()
        LogService.log(workspace_id, actor, 'calendar.event_updated', {'event_id': str(event.pk)})
        return event

    @staticmethod
    @transaction.atomic
    def delete_event(workspace_id, actor: User, event_id):
        PermissionService.assert_permission(workspace_id, actor, 'write')
        try:
            event = WorkspaceCalendarEvent.objects.get(pk=event_id, workspace_id=workspace_id)
        except WorkspaceCalendarEvent.DoesNotExist:
            raise NotFound('Event not found.')
        event.delete()
        LogService.log(workspace_id, actor, 'calendar.event_deleted', {'event_id': str(event_id)})

    @staticmethod
    def list_events(workspace_id, actor: User, start=None, end=None):
        PermissionService.assert_member(workspace_id, actor)
        qs = WorkspaceCalendarEvent.objects.filter(workspace_id=workspace_id)
        if start:
            qs = qs.filter(end_at__gte=start)
        if end:
            qs = qs.filter(start_at__lte=end)
        return qs


# ─────────────────────────────────────────────────────────────────────────────
# 3.6  FileService
# ─────────────────────────────────────────────────────────────────────────────

class FileService:

    @staticmethod
    def _cipher():
        from cryptography.fernet import Fernet

        key = settings.WORKSPACE_FILE_ENCRYPTION_KEY
        if not key:
            key = base64.urlsafe_b64encode(hashlib.sha256(settings.SECRET_KEY.encode('utf-8')).digest()).decode('ascii')
        return Fernet(key.encode('ascii'))

    @staticmethod
    def _validate_name(name: str, field_name: str) -> str:
        name = str(name or '').strip()
        if not name:
            raise ValidationError({field_name: f'{field_name.replace("_", " ").capitalize()} is required.'})
        if name in {'.', '..'} or any(character in name for character in ('/', '\\', '\x00')):
            raise ValidationError({field_name: 'Names cannot contain path separators or traversal segments.'})
        return name

    @staticmethod
    def _build_path(workspace_id, file_id) -> str:
        return f'workspaces/{workspace_id}/files/{file_id}.bin'

    @staticmethod
    @transaction.atomic
    def create_folder(workspace_id, actor: User, parent_id, name: str) -> WorkspaceFolder:
        PermissionService.assert_permission(workspace_id, actor, 'manage_files')
        name = FileService._validate_name(name, 'name')
        parent = None
        if parent_id:
            try:
                parent = WorkspaceFolder.objects.get(pk=parent_id, workspace_id=workspace_id)
            except WorkspaceFolder.DoesNotExist:
                raise NotFound('Parent folder not found.')
        if WorkspaceFolder.objects.filter(workspace_id=workspace_id, parent=parent, name=name).exists():
            raise ValidationError({'name': 'A folder with this name already exists here.'})
        folder = WorkspaceFolder.objects.create(workspace_id=workspace_id, parent=parent, name=name)
        LogService.log(workspace_id, actor, 'file.folder_created', {'folder_id': str(folder.pk), 'name': name})
        return folder

    @staticmethod
    @transaction.atomic
    def upload_file(workspace_id, actor: User, folder_id, name: str, content, mime_type: str) -> WorkspaceFile:
        """Encrypt and persist uploaded binary content with governed metadata."""
        PermissionService.assert_permission(workspace_id, actor, 'manage_files')
        name = FileService._validate_name(name, 'name')
        size = content.size
        if size > settings.WORKSPACE_FILE_MAX_BYTES:
            raise ValidationError({'content': f'Files may not exceed {settings.WORKSPACE_FILE_MAX_BYTES} bytes.'})
        folder = None
        if folder_id:
            try:
                folder = WorkspaceFolder.objects.get(pk=folder_id, workspace_id=workspace_id)
            except WorkspaceFolder.DoesNotExist:
                raise NotFound('Folder not found.')
        # Reserve a UUID so the path can reference the id before save
        file_id = __import__('uuid').uuid4()
        path = FileService._build_path(workspace_id, file_id)
        encrypted_content = FileService._cipher().encrypt(content.read())
        default_storage.save(path, ContentFile(encrypted_content))
        wf = WorkspaceFile.objects.create(
            id=file_id,
            workspace_id=workspace_id,
            folder=folder,
            name=name,
            path=path,
            size=size,
            mime_type=mime_type,
            uploaded_by=actor,
        )
        LogService.log(workspace_id, actor, 'file.uploaded', {'file_id': str(wf.pk), 'name': name, 'size': size, 'encrypted': True})
        return wf

    @staticmethod
    def download_file(workspace_id, actor: User, file_id):
        PermissionService.assert_workspace_section(workspace_id, actor, 'files')
        try:
            workspace_file = WorkspaceFile.objects.get(pk=file_id, workspace_id=workspace_id)
        except WorkspaceFile.DoesNotExist:
            raise NotFound('File not found.')
        if not default_storage.exists(workspace_file.path):
            raise NotFound('File content is unavailable.')
        with default_storage.open(workspace_file.path, 'rb') as stored_file:
            decrypted_content = FileService._cipher().decrypt(stored_file.read())
        LogService.log(workspace_id, actor, 'file.downloaded', {'file_id': str(workspace_file.pk), 'name': workspace_file.name})
        return BytesIO(decrypted_content), workspace_file

    @staticmethod
    @transaction.atomic
    def delete_file(workspace_id, actor: User, file_id):
        PermissionService.assert_permission(workspace_id, actor, 'manage_files')
        try:
            wf = WorkspaceFile.objects.get(pk=file_id, workspace_id=workspace_id)
        except WorkspaceFile.DoesNotExist:
            raise NotFound('File not found.')
        if default_storage.exists(wf.path):
            default_storage.delete(wf.path)
        wf.delete()
        LogService.log(workspace_id, actor, 'file.deleted', {'file_id': str(file_id)})

    @staticmethod
    def list_files(workspace_id, actor: User, folder_id=None):
        PermissionService.assert_member(workspace_id, actor)
        qs = WorkspaceFile.objects.filter(workspace_id=workspace_id)
        if folder_id:
            qs = qs.filter(folder_id=folder_id)
        else:
            qs = qs.filter(folder__isnull=True)
        return qs.select_related('uploaded_by')

    @staticmethod
    def list_folders(workspace_id, actor: User, parent_id=None):
        PermissionService.assert_member(workspace_id, actor)
        return WorkspaceFolder.objects.filter(workspace_id=workspace_id, parent_id=parent_id)


# ─────────────────────────────────────────────────────────────────────────────
# 3.8  SettingsService
# ─────────────────────────────────────────────────────────────────────────────

class SettingsService:

    @staticmethod
    def get_settings(workspace_id, actor: User) -> dict:
        PermissionService.assert_member(workspace_id, actor)
        entries = WorkspaceSetting.objects.filter(workspace_id=workspace_id)
        return {e.key: e.value for e in entries}

    @staticmethod
    @transaction.atomic
    def update_settings(workspace_id, actor: User, payload: dict) -> dict:
        PermissionService.assert_permission(workspace_id, actor, 'manage_settings')
        for key, value in payload.items():
            WorkspaceSetting.objects.update_or_create(
                workspace_id=workspace_id, key=key,
                defaults={'value': str(value)}
            )
        LogService.log(workspace_id, actor, 'settings.updated', {'keys': list(payload.keys())})
        return SettingsService.get_settings(workspace_id, actor)

    @staticmethod
    @transaction.atomic
    def update_modules(workspace_id, actor: User, payload: dict):
        """payload = { module_key: True/False, ... }"""
        PermissionService.assert_permission(workspace_id, actor, 'manage_modules')
        updated = []
        for module_key, enabled in payload.items():
            mod, _ = WorkspaceModule.objects.get_or_create(
                workspace_id=workspace_id, module_key=module_key
            )
            mod.enabled = bool(enabled)
            mod.save()
            updated.append({'module_key': module_key, 'enabled': mod.enabled})
        LogService.log(workspace_id, actor, 'modules.updated', {'modules': updated})
        return WorkspaceModule.objects.filter(workspace_id=workspace_id)
