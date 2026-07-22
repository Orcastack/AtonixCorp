"""
Workspace models.
Workspace tables are workspace-scoped, and the workspace root can optionally link to a finance entity.
"""
import secrets
import uuid
from django.db import models
from django.contrib.auth.models import User


# ─────────────────────────────────────────────────────────────────────────────
# Enumerations
# ─────────────────────────────────────────────────────────────────────────────

class WorkspaceTier(models.TextChoices):
    FREE       = 'free',       'Free'
    PRO        = 'pro',        'Pro'
    ENTERPRISE = 'enterprise', 'Enterprise'


class WorkspaceStatus(models.TextChoices):
    ACTIVE    = 'active',    'Active'
    SUSPENDED = 'suspended', 'Suspended'
    ARCHIVED  = 'archived',  'Archived'
    DELETED   = 'deleted',   'Deleted'


class MemberRole(models.TextChoices):
    OWNER  = 'owner',  'Owner'
    ADMIN  = 'admin',  'Admin'
    MEMBER = 'member', 'Member'
    VIEWER = 'viewer', 'Viewer'


class ParticipantStatus(models.TextChoices):
    INVITED  = 'invited',  'Invited'
    ACCEPTED = 'accepted', 'Accepted'
    DECLINED = 'declined', 'Declined'


class CalendarEventType(models.TextChoices):
    MEETING  = 'meeting',  'Meeting'
    REMINDER = 'reminder', 'Reminder'
    TASK     = 'task',     'Task'
    CUSTOM   = 'custom',   'Custom'


# ─────────────────────────────────────────────────────────────────────────────
# 2.1  Workspace
# ─────────────────────────────────────────────────────────────────────────────

class Workspace(models.Model):
    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_workspaces')
    linked_entity = models.OneToOneField('finances.Entity', on_delete=models.SET_NULL, null=True, blank=True, related_name='linked_workspace')
    workspace_code = models.CharField(max_length=20, unique=True, editable=False, db_index=True, blank=True)
    name        = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    tier        = models.CharField(max_length=20, choices=WorkspaceTier.choices, default=WorkspaceTier.FREE)
    status      = models.CharField(max_length=20, choices=WorkspaceStatus.choices, default=WorkspaceStatus.ACTIVE)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} ({self.tier})'

    def save(self, *args, **kwargs):
        if self.pk:
            stored_code = Workspace.objects.filter(pk=self.pk).values_list('workspace_code', flat=True).first()
            if stored_code:
                self.workspace_code = stored_code
        if not self.workspace_code:
            from atonixcorp.models import generate_identity_code

            self.workspace_code = generate_identity_code('WSP')
        super().save(*args, **kwargs)


# ─────────────────────────────────────────────────────────────────────────────
# 2.2  WorkspaceMember
# ─────────────────────────────────────────────────────────────────────────────

class WorkspaceMember(models.Model):
    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace    = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='members')
    user         = models.ForeignKey(User, on_delete=models.CASCADE, related_name='workspace_memberships')
    member_code  = models.CharField(max_length=6, unique=True, editable=False, null=True, blank=True)
    role         = models.CharField(max_length=20, choices=MemberRole.choices, null=True, blank=True, default=None)
    status       = models.CharField(max_length=20, choices=ParticipantStatus.choices, default=ParticipantStatus.ACCEPTED)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('workspace', 'user')
        ordering = ['created_at']

    def __str__(self):
        role_label = self.role or 'invited'
        return f'{self.user.email} → {self.workspace.name} ({role_label})'

    @staticmethod
    def generate_member_code():
        while True:
            member_code = f'{secrets.randbelow(1_000_000):06d}'
            if not WorkspaceMember.objects.filter(member_code=member_code).exists():
                return member_code

    def save(self, *args, **kwargs):
        if not self.member_code:
            self.member_code = self.generate_member_code()
        super().save(*args, **kwargs)


# ─────────────────────────────────────────────────────────────────────────────
# 2.3  WorkspaceGroup
# ─────────────────────────────────────────────────────────────────────────────

class WorkspaceGroup(models.Model):
    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace   = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='groups')
    name        = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    owner       = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='workspace_department_ownerships')
    cost_center = models.CharField(max_length=64, blank=True, default='')
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('workspace', 'name')
        ordering = ['name']

    def __str__(self):
        return f'{self.workspace.name} / {self.name}'


# ─────────────────────────────────────────────────────────────────────────────
# 2.4  WorkspaceGroupMember
# ─────────────────────────────────────────────────────────────────────────────

class WorkspaceGroupMember(models.Model):
    id    = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group = models.ForeignKey(WorkspaceGroup, on_delete=models.CASCADE, related_name='group_members')
    user  = models.ForeignKey(User, on_delete=models.CASCADE, related_name='workspace_group_memberships')

    class Meta:
        unique_together = ('group', 'user')

    def __str__(self):
        return f'{self.user.email} → {self.group.name}'


# ─────────────────────────────────────────────────────────────────────────────
# 2.5  WorkspaceMeeting
# ─────────────────────────────────────────────────────────────────────────────

class WorkspaceMeeting(models.Model):
    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace   = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='meetings')
    title       = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    start_at    = models.DateTimeField()
    end_at      = models.DateTimeField()
    created_by  = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_meetings')
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['start_at']

    def __str__(self):
        return f'{self.workspace.name}: {self.title}'


# ─────────────────────────────────────────────────────────────────────────────
# 2.6  WorkspaceMeetingParticipant
# ─────────────────────────────────────────────────────────────────────────────

class WorkspaceMeetingParticipant(models.Model):
    id      = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    meeting = models.ForeignKey(WorkspaceMeeting, on_delete=models.CASCADE, related_name='participants')
    user    = models.ForeignKey(User, on_delete=models.CASCADE, related_name='meeting_participations')
    status  = models.CharField(max_length=20, choices=ParticipantStatus.choices, default=ParticipantStatus.INVITED)

    class Meta:
        unique_together = ('meeting', 'user')

    def __str__(self):
        return f'{self.user.email} → {self.meeting.title} ({self.status})'


# ─────────────────────────────────────────────────────────────────────────────
# 2.7  WorkspaceCalendarEvent
# ─────────────────────────────────────────────────────────────────────────────

class WorkspaceCalendarEvent(models.Model):
    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace   = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='calendar_events')
    title       = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    start_at    = models.DateTimeField()
    end_at      = models.DateTimeField()
    type        = models.CharField(max_length=20, choices=CalendarEventType.choices, default=CalendarEventType.CUSTOM)
    created_by  = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_calendar_events')
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['start_at']

    def __str__(self):
        return f'{self.workspace.name}: {self.title}'


# ─────────────────────────────────────────────────────────────────────────────
# 2.8  WorkspaceFolder
# ─────────────────────────────────────────────────────────────────────────────

class WorkspaceFolder(models.Model):
    id        = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='folders')
    parent    = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    name      = models.CharField(max_length=255)

    class Meta:
        unique_together = ('workspace', 'parent', 'name')

    def __str__(self):
        return f'{self.workspace.name}/{self.name}'


# ─────────────────────────────────────────────────────────────────────────────
# 2.9  WorkspaceFile
# ─────────────────────────────────────────────────────────────────────────────

class WorkspaceFile(models.Model):
    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace   = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='files')
    folder      = models.ForeignKey(WorkspaceFolder, on_delete=models.SET_NULL, null=True, blank=True, related_name='files')
    name        = models.CharField(max_length=255)
    path        = models.CharField(max_length=1024)   # S3/Blob path
    size        = models.BigIntegerField(default=0)    # bytes
    mime_type   = models.CharField(max_length=127, blank=True, default='')
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='uploaded_workspace_files')
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.workspace.name}/{self.name}'


# ─────────────────────────────────────────────────────────────────────────────
# 2.10  WorkspaceModule
# ─────────────────────────────────────────────────────────────────────────────

DEFAULT_MODULES = [
    'overview', 'members', 'groups', 'meetings',
    'calendar', 'files', 'permissions', 'settings',
    'email', 'marketing',
]


class WorkspaceModule(models.Model):
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace  = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='modules')
    module_key = models.CharField(max_length=100)
    enabled    = models.BooleanField(default=True)

    class Meta:
        unique_together = ('workspace', 'module_key')

    def __str__(self):
        return f'{self.workspace.name} / {self.module_key} ({"on" if self.enabled else "off"})'


# ─────────────────────────────────────────────────────────────────────────────
# 2.11  WorkspaceSetting
# ─────────────────────────────────────────────────────────────────────────────

class WorkspaceSetting(models.Model):
    id        = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='settings_entries')
    key       = models.CharField(max_length=255)
    value     = models.TextField(blank=True, default='')

    class Meta:
        unique_together = ('workspace', 'key')

    def __str__(self):
        return f'{self.workspace.name} / {self.key}'


# ─────────────────────────────────────────────────────────────────────────────
# 2.12  WorkspaceLog
# ─────────────────────────────────────────────────────────────────────────────

class WorkspaceLog(models.Model):
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace  = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='logs')
    actor      = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='workspace_log_entries')
    action     = models.CharField(max_length=255)
    metadata   = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'[{self.workspace.name}] {self.action} by {self.actor_id}'
