"""
Workspace serializers.
Input serializers validate incoming payloads.
Output serializers render clean API responses.
"""
from django.apps import apps
from django.contrib.auth.models import User
from rest_framework import serializers

from .models import (
    Workspace, WorkspaceMember, WorkspaceGroup, WorkspaceGroupMember,
    WorkspaceMeeting, WorkspaceMeetingParticipant,
    WorkspaceCalendarEvent, WorkspaceFile, WorkspaceFolder,
    WorkspaceModule, WorkspaceSetting, WorkspaceLog,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

class UserBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model  = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name')


# ─────────────────────────────────────────────────────────────────────────────
# Workspace
# ─────────────────────────────────────────────────────────────────────────────

class WorkspaceSerializer(serializers.ModelSerializer):
    owner = UserBriefSerializer(read_only=True)
    linked_entity_id = serializers.IntegerField(read_only=True)
    linked_entity_name = serializers.ReadOnlyField(source='linked_entity.name')
    linked_entity_industry = serializers.ReadOnlyField(source='linked_entity.industry')
    business_type = serializers.SerializerMethodField()
    country_of_incorporation = serializers.SerializerMethodField()
    currency = serializers.SerializerMethodField()
    fiscal_year = serializers.SerializerMethodField()
    tax_regime = serializers.SerializerMethodField()
    component_count = serializers.SerializerMethodField()
    members_count = serializers.SerializerMethodField()
    departments_count = serializers.SerializerMethodField()
    clients_count = serializers.SerializerMethodField()
    workspace_mode = serializers.SerializerMethodField()
    workspace_mode_label = serializers.SerializerMethodField()
    workspace_type = serializers.ReadOnlyField(source='linked_entity.workspace_type')
    workspace_type_label = serializers.SerializerMethodField()
    hierarchy_metadata = serializers.ReadOnlyField(source='linked_entity.hierarchy_metadata')
    dashboard_config = serializers.ReadOnlyField(source='linked_entity.dashboard_config')
    rbac_config = serializers.ReadOnlyField(source='linked_entity.rbac_config')

    class Meta:
        model  = Workspace
        fields = (
            'id', 'workspace_code', 'owner', 'name', 'description', 'tier', 'status',
            'linked_entity_id', 'linked_entity_name', 'linked_entity_industry',
            'business_type', 'country_of_incorporation', 'currency', 'fiscal_year',
            'tax_regime', 'component_count',
            'members_count', 'departments_count', 'clients_count',
            'workspace_mode', 'workspace_mode_label', 'workspace_type', 'workspace_type_label',
            'hierarchy_metadata', 'dashboard_config', 'rbac_config',
            'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'workspace_code', 'owner', 'created_at', 'updated_at')

    @staticmethod
    def _format_fiscal_year(fiscal_year_end):
        if not fiscal_year_end:
            return None

        month = fiscal_year_end.month
        day = fiscal_year_end.day
        if month == 12 and day == 31:
            return 'Jan–Dec'
        if month == 3 and day == 31:
            return 'Apr–Mar'
        if month == 6 and day == 30:
            return 'Jul–Jun'
        if month == 9 and day == 30:
            return 'Oct–Sep'

        start_month = (month % 12) + 1
        import calendar
        return f'{calendar.month_abbr[start_month]}–{calendar.month_abbr[month]}'

    def get_business_type(self, workspace):
        linked_entity = getattr(workspace, 'linked_entity', None)
        organization = getattr(linked_entity, 'organization', None)
        if organization and organization.industry:
            return organization.industry
        if linked_entity and getattr(linked_entity, 'entity_type', None):
            return linked_entity.get_entity_type_display() if hasattr(linked_entity, 'get_entity_type_display') else linked_entity.entity_type
        return 'Not Set'

    def get_country_of_incorporation(self, workspace):
        linked_entity = getattr(workspace, 'linked_entity', None)
        if linked_entity and linked_entity.country:
            return linked_entity.country
        organization = getattr(linked_entity, 'organization', None)
        return getattr(organization, 'primary_country', None) or 'Not Set'

    def get_currency(self, workspace):
        linked_entity = getattr(workspace, 'linked_entity', None)
        if linked_entity and linked_entity.local_currency:
            return linked_entity.local_currency
        organization = getattr(linked_entity, 'organization', None)
        return getattr(organization, 'primary_currency', None) or 'USD'

    def get_fiscal_year(self, workspace):
        linked_entity = getattr(workspace, 'linked_entity', None)
        if not linked_entity:
            return 'Not Set'
        fiscal_year = self._format_fiscal_year(getattr(linked_entity, 'fiscal_year_end', None))
        return fiscal_year or 'Not Set'

    def get_tax_regime(self, workspace):
        linked_entity = getattr(workspace, 'linked_entity', None)
        if not linked_entity:
            return 'Not Set'

        tax_profile = linked_entity.tax_profiles.order_by('-updated_at').first()
        if not tax_profile:
            return 'Not Set'

        regime_codes = list(getattr(tax_profile, 'active_regime_codes', []) or [])
        if not regime_codes:
            regime_codes = [code for code in tax_profile.registered_regimes or [] if code]

        if not regime_codes:
            return 'Not Set'

        TaxRegimeRegistry = apps.get_model('finances', 'TaxRegimeRegistry')
        registry = TaxRegimeRegistry.objects.filter(
            regime_code__in=regime_codes,
            country=tax_profile.country,
        ).order_by('regime_name').first()

        if registry:
            return registry.regime_name
        return regime_codes[0]

    def get_component_count(self, workspace):
        annotated = getattr(workspace, 'component_count', None)
        if annotated is not None:
            return annotated
        if hasattr(workspace, 'modules'):
            return workspace.modules.filter(enabled=True).count()
        linked_entity = getattr(workspace, 'linked_entity', None)
        enabled_modules = getattr(linked_entity, 'enabled_modules', None)
        return len(enabled_modules) if isinstance(enabled_modules, list) else 0

    def get_members_count(self, workspace):
        return getattr(workspace, 'members_count', None) if getattr(workspace, 'members_count', None) is not None else workspace.members.count()

    def get_departments_count(self, workspace):
        return getattr(workspace, 'departments_count', None) if getattr(workspace, 'departments_count', None) is not None else workspace.groups.count()

    def get_clients_count(self, workspace):
        annotated = getattr(workspace, 'clients_count', None)
        if annotated is not None:
                        return annotated
        organization = getattr(getattr(workspace, 'linked_entity', None), 'organization', None)
        return organization.clients.count() if organization else 0

    def get_workspace_mode(self, workspace):
        linked_entity = getattr(workspace, 'linked_entity', None)
        return getattr(linked_entity, 'workspace_mode', None) or 'accounting'

    def get_workspace_mode_label(self, workspace):
        mode = self.get_workspace_mode(workspace)
        return {
            'accounting': 'Accounting',
            'equity': 'Equity Management',
            'combined': 'Combined',
            'standalone': 'Standalone',
            'workspace': 'Workspace',
        }.get(mode, 'Accounting')

    def get_workspace_type_label(self, workspace):
        linked_entity = getattr(workspace, 'linked_entity', None)
        if not linked_entity:
            return None
        hierarchy_metadata = getattr(linked_entity, 'hierarchy_metadata', {}) or {}
        return hierarchy_metadata.get('workspace_type_label') or getattr(linked_entity, 'workspace_type', None)


class WorkspaceCreateSerializer(serializers.Serializer):
    name        = serializers.CharField(max_length=255)
    description = serializers.CharField(allow_blank=True, required=False, default='')
    linked_entity_id = serializers.IntegerField(required=False, allow_null=True)
    tier        = serializers.ChoiceField(
        choices=['free', 'pro', 'enterprise'],
        required=False,
        default='free',
    )


class WorkspaceUpdateSerializer(serializers.Serializer):
    name        = serializers.CharField(max_length=255, required=False)
    description = serializers.CharField(allow_blank=True, required=False)
    linked_entity_id = serializers.IntegerField(required=False, allow_null=True)


class TierUpdateSerializer(serializers.Serializer):
    tier = serializers.ChoiceField(choices=['free', 'pro', 'enterprise'])


class StatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=['active', 'suspended', 'archived', 'deleted'])


# ─────────────────────────────────────────────────────────────────────────────
# Members
# ─────────────────────────────────────────────────────────────────────────────

class WorkspaceMemberSerializer(serializers.ModelSerializer):
    user = UserBriefSerializer(read_only=True)
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    member_code = serializers.CharField(read_only=True)
    departments = serializers.SerializerMethodField()

    class Meta:
        model  = WorkspaceMember
        fields = ('id', 'member_code', 'user_id', 'user', 'role', 'departments', 'status', 'created_at')
        read_only_fields = ('id', 'created_at')

    def get_departments(self, obj):
        department_map = self.context.get('department_map') or {}
        department_names = department_map.get(obj.user_id, [])
        if not department_names:
            return '—'
        return ', '.join(department_names)


class MemberAddSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    role    = serializers.ChoiceField(choices=['admin', 'member', 'viewer'])


class MemberRoleSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=['admin', 'member', 'viewer'])


# ─────────────────────────────────────────────────────────────────────────────
# Departments
# ─────────────────────────────────────────────────────────────────────────────

class WorkspaceDepartmentMemberSerializer(serializers.ModelSerializer):
    user = UserBriefSerializer(read_only=True)

    class Meta:
        model  = WorkspaceGroupMember
        fields = ('id', 'user')


class WorkspaceDepartmentSerializer(serializers.ModelSerializer):
    members = WorkspaceDepartmentMemberSerializer(source='group_members', many=True, read_only=True)
    owner = UserBriefSerializer(read_only=True)

    class Meta:
        model  = WorkspaceGroup
        fields = ('id', 'name', 'description', 'owner', 'cost_center', 'created_at', 'members')
        read_only_fields = ('id', 'created_at')


class DepartmentCreateSerializer(serializers.Serializer):
    name        = serializers.CharField(max_length=255)
    description = serializers.CharField(allow_blank=True, required=False, default='')
    owner_user_id = serializers.IntegerField(required=False, allow_null=True)
    cost_center = serializers.CharField(max_length=64, required=False, allow_blank=True, default='')


class DepartmentUpdateSerializer(serializers.Serializer):
    name        = serializers.CharField(max_length=255, required=False)
    description = serializers.CharField(allow_blank=True, required=False)
    owner_user_id = serializers.IntegerField(required=False, allow_null=True)
    cost_center = serializers.CharField(max_length=64, required=False, allow_blank=True)


class DepartmentMemberSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()


WorkspaceGroupMemberSerializer = WorkspaceDepartmentMemberSerializer
WorkspaceGroupSerializer = WorkspaceDepartmentSerializer
GroupCreateSerializer = DepartmentCreateSerializer
GroupUpdateSerializer = DepartmentUpdateSerializer
GroupMemberSerializer = DepartmentMemberSerializer


# ─────────────────────────────────────────────────────────────────────────────
# Meetings
# ─────────────────────────────────────────────────────────────────────────────

class WorkspaceMeetingParticipantSerializer(serializers.ModelSerializer):
    user = UserBriefSerializer(read_only=True)

    class Meta:
        model  = WorkspaceMeetingParticipant
        fields = ('id', 'user', 'status')


class WorkspaceMeetingSerializer(serializers.ModelSerializer):
    created_by   = UserBriefSerializer(read_only=True)
    participants = WorkspaceMeetingParticipantSerializer(many=True, read_only=True)

    class Meta:
        model  = WorkspaceMeeting
        fields = ('id', 'title', 'description', 'start_at', 'end_at', 'created_by', 'participants', 'created_at')
        read_only_fields = ('id', 'created_by', 'created_at')


class MeetingCreateSerializer(serializers.Serializer):
    title       = serializers.CharField(max_length=255)
    description = serializers.CharField(allow_blank=True, required=False, default='')
    start_at    = serializers.DateTimeField()
    end_at      = serializers.DateTimeField()

    def validate(self, data):
        if data['end_at'] <= data['start_at']:
            raise serializers.ValidationError('end_at must be after start_at.')
        return data


class MeetingUpdateSerializer(serializers.Serializer):
    title       = serializers.CharField(max_length=255, required=False)
    description = serializers.CharField(allow_blank=True, required=False)
    start_at    = serializers.DateTimeField(required=False)
    end_at      = serializers.DateTimeField(required=False)


# ─────────────────────────────────────────────────────────────────────────────
# Calendar
# ─────────────────────────────────────────────────────────────────────────────

class WorkspaceCalendarEventSerializer(serializers.ModelSerializer):
    created_by = UserBriefSerializer(read_only=True)

    class Meta:
        model  = WorkspaceCalendarEvent
        fields = ('id', 'title', 'description', 'start_at', 'end_at', 'type', 'created_by', 'created_at')
        read_only_fields = ('id', 'created_by', 'created_at')


class CalendarEventCreateSerializer(serializers.Serializer):
    title       = serializers.CharField(max_length=255)
    description = serializers.CharField(allow_blank=True, required=False, default='')
    start_at    = serializers.DateTimeField()
    end_at      = serializers.DateTimeField()
    type        = serializers.ChoiceField(choices=['meeting', 'reminder', 'task', 'custom'], required=False, default='custom')

    def validate(self, data):
        if data['end_at'] <= data['start_at']:
            raise serializers.ValidationError('end_at must be after start_at.')
        return data


class CalendarEventUpdateSerializer(serializers.Serializer):
    title       = serializers.CharField(max_length=255, required=False)
    description = serializers.CharField(allow_blank=True, required=False)
    start_at    = serializers.DateTimeField(required=False)
    end_at      = serializers.DateTimeField(required=False)
    type        = serializers.ChoiceField(choices=['meeting', 'reminder', 'task', 'custom'], required=False)


# ─────────────────────────────────────────────────────────────────────────────
# Files & Folders
# ─────────────────────────────────────────────────────────────────────────────

class WorkspaceFolderSerializer(serializers.ModelSerializer):
    class Meta:
        model  = WorkspaceFolder
        fields = ('id', 'name', 'parent')
        read_only_fields = ('id',)


class WorkspaceFileSerializer(serializers.ModelSerializer):
    uploaded_by = UserBriefSerializer(read_only=True)

    class Meta:
        model  = WorkspaceFile
        fields = ('id', 'name', 'path', 'size', 'mime_type', 'folder', 'uploaded_by', 'created_at')
        read_only_fields = ('id', 'path', 'uploaded_by', 'created_at')


class FolderCreateSerializer(serializers.Serializer):
    name      = serializers.CharField(max_length=255)
    parent_id = serializers.UUIDField(required=False, allow_null=True)


class FileUploadSerializer(serializers.Serializer):
    content   = serializers.FileField(write_only=True)
    name      = serializers.CharField(max_length=255, required=False, allow_blank=True)
    mime_type = serializers.CharField(max_length=127, required=False, default='')
    folder_id = serializers.UUIDField(required=False, allow_null=True)

    def validate(self, data):
        content = data['content']
        if content.size <= 0:
            raise serializers.ValidationError({'content': 'Uploaded files cannot be empty.'})
        data['name'] = data.get('name') or content.name
        if not data.get('mime_type'):
            data['mime_type'] = getattr(content, 'content_type', '') or 'application/octet-stream'
        return data


# ─────────────────────────────────────────────────────────────────────────────
# Modules
# ─────────────────────────────────────────────────────────────────────────────

class WorkspaceModuleSerializer(serializers.ModelSerializer):
    class Meta:
        model  = WorkspaceModule
        fields = ('id', 'module_key', 'enabled')
        read_only_fields = ('id',)


class ModulesUpdateSerializer(serializers.Serializer):
    """
    Payload: { "module_key": true/false, ... }
    Accepts any key; unknown module keys will be created on-the-fly.
    """
    def to_internal_value(self, data):
        if not isinstance(data, dict):
            raise serializers.ValidationError('Expected a JSON object.')
        for key, value in data.items():
            if not isinstance(value, bool):
                raise serializers.ValidationError(f'Value for "{key}" must be a boolean.')
        return data


# ─────────────────────────────────────────────────────────────────────────────
# Settings
# ─────────────────────────────────────────────────────────────────────────────

class WorkspaceSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model  = WorkspaceSetting
        fields = ('id', 'key', 'value')
        read_only_fields = ('id',)


# ─────────────────────────────────────────────────────────────────────────────
# Logs
# ─────────────────────────────────────────────────────────────────────────────

class WorkspaceLogSerializer(serializers.ModelSerializer):
    actor = UserBriefSerializer(read_only=True)

    class Meta:
        model  = WorkspaceLog
        fields = ('id', 'actor', 'action', 'metadata', 'created_at')
        read_only_fields = ('id', 'actor', 'action', 'metadata', 'created_at')
