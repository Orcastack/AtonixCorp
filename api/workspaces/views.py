"""
Workspace API views.
Every view:
  1. Requires authentication (IsAuthenticated).
  2. Resolves and validates workspace membership via PermissionService.
  3. Delegates all mutations to the appropriate service.
  4. Returns consistent JSON responses.

No cross-system data access. No role bypassing.
"""
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.http import FileResponse
from rest_framework.views import APIView
from rest_framework.exceptions import NotFound

from .models import Workspace, WorkspaceLog
from .serializers import (
    CalendarEventCreateSerializer, CalendarEventUpdateSerializer,
    DepartmentCreateSerializer, DepartmentMemberSerializer, DepartmentUpdateSerializer,
    FileUploadSerializer, FolderCreateSerializer,
    MeetingCreateSerializer, MeetingUpdateSerializer,
    MemberAddSerializer, MemberRoleSerializer,
    ModulesUpdateSerializer,
    TierUpdateSerializer, StatusUpdateSerializer,
    WorkspaceCalendarEventSerializer,
    WorkspaceCreateSerializer, WorkspaceUpdateSerializer,
    WorkspaceDepartmentSerializer,
    WorkspaceFileSerializer, WorkspaceFolderSerializer,
    WorkspaceLogSerializer,
    WorkspaceMeetingSerializer,
    WorkspaceMemberSerializer,
    WorkspaceModuleSerializer,
    WorkspaceSerializer,
)
from .services import (
    CalendarService, DepartmentService, FileService,
    LogService, MeetingService, MemberService,
    PermissionService, SettingsService, WorkspaceService,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get_user_or_404(user_id: int) -> User:
    try:
        return User.objects.get(pk=user_id)
    except User.DoesNotExist:
        raise NotFound(f'User {user_id} not found.')


def _get_workspace_or_404(workspace_id) -> Workspace:
    try:
        return Workspace.objects.get(pk=workspace_id)
    except Workspace.DoesNotExist:
        raise NotFound('Workspace not found.')


def _resolve_workspace_id_or_404(workspace_ref):
    return WorkspaceService.resolve_workspace_id(workspace_ref)


def _workspace_member_serializer_context(workspace_id):
    return {
        'department_map': MemberService.member_department_map(workspace_id),
    }


# ─────────────────────────────────────────────────────────────────────────────
# POST /workspaces          — create
# GET  /workspaces          — list user's workspaces
# ─────────────────────────────────────────────────────────────────────────────

class WorkspaceListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        workspaces = WorkspaceService.list_user_workspaces(request.user)
        return Response(WorkspaceSerializer(workspaces, many=True).data)

    def post(self, request):
        ser = WorkspaceCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ws = WorkspaceService.create_workspace(request.user, ser.validated_data)
        return Response(WorkspaceSerializer(ws).data, status=status.HTTP_201_CREATED)


# ─────────────────────────────────────────────────────────────────────────────
# GET   /workspaces/{id}    — retrieve
# PATCH /workspaces/{id}    — update metadata
# ─────────────────────────────────────────────────────────────────────────────

class WorkspaceDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, workspace_id):
        workspace_id = _resolve_workspace_id_or_404(workspace_id)
        PermissionService.assert_workspace_section(workspace_id, request.user, 'overview')
        ws = WorkspaceService.get_workspace(workspace_id, request.user)
        return Response(WorkspaceSerializer(ws).data)

    def patch(self, request, workspace_id):
        workspace_id = _resolve_workspace_id_or_404(workspace_id)
        ser = WorkspaceUpdateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ws = WorkspaceService.update_workspace(workspace_id, request.user, ser.validated_data)
        return Response(WorkspaceSerializer(ws).data)


# ─────────────────────────────────────────────────────────────────────────────
# PATCH /workspaces/{id}/tier
# ─────────────────────────────────────────────────────────────────────────────

class WorkspaceTierView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, workspace_id):
        workspace_id = _resolve_workspace_id_or_404(workspace_id)
        ser = TierUpdateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ws = WorkspaceService.change_tier(workspace_id, request.user, ser.validated_data['tier'])
        return Response(WorkspaceSerializer(ws).data)


# ─────────────────────────────────────────────────────────────────────────────
# PATCH /workspaces/{id}/status
# ─────────────────────────────────────────────────────────────────────────────

class WorkspaceStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, workspace_id):
        workspace_id = _resolve_workspace_id_or_404(workspace_id)
        ser = StatusUpdateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ws = WorkspaceService.change_status(workspace_id, request.user, ser.validated_data['status'])
        return Response(WorkspaceSerializer(ws).data)


# ─────────────────────────────────────────────────────────────────────────────
# GET  /workspaces/{id}/members       — list
# POST /workspaces/{id}/members       — add
# ─────────────────────────────────────────────────────────────────────────────

class WorkspaceMemberListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, workspace_id):
        workspace_id = _resolve_workspace_id_or_404(workspace_id)
        PermissionService.assert_workspace_section(workspace_id, request.user, 'members')
        members = MemberService.list_members(workspace_id, request.user)
        return Response(WorkspaceMemberSerializer(members, many=True, context=_workspace_member_serializer_context(workspace_id)).data)

    def post(self, request, workspace_id):
        workspace_id = _resolve_workspace_id_or_404(workspace_id)
        ser = MemberAddSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        user = _get_user_or_404(ser.validated_data['user_id'])
        member = MemberService.add_member(workspace_id, request.user, user, ser.validated_data['role'])
        return Response(WorkspaceMemberSerializer(member, context=_workspace_member_serializer_context(workspace_id)).data, status=status.HTTP_201_CREATED)


# ─────────────────────────────────────────────────────────────────────────────
# PATCH  /workspaces/{id}/members/{user_id}   — update role
# DELETE /workspaces/{id}/members/{user_id}   — remove
# ─────────────────────────────────────────────────────────────────────────────

class WorkspaceMemberDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, workspace_id, user_id):
        workspace_id = _resolve_workspace_id_or_404(workspace_id)
        ser = MemberRoleSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        target = _get_user_or_404(user_id)
        member = MemberService.update_role(workspace_id, request.user, target, ser.validated_data['role'])
        return Response(WorkspaceMemberSerializer(member, context=_workspace_member_serializer_context(workspace_id)).data)

    def delete(self, request, workspace_id, user_id):
        workspace_id = _resolve_workspace_id_or_404(workspace_id)
        target = _get_user_or_404(user_id)
        MemberService.remove_member(workspace_id, request.user, target)
        return Response(status=status.HTTP_204_NO_CONTENT)


# ─────────────────────────────────────────────────────────────────────────────
# GET  /workspaces/{id}/groups   — list
# POST /workspaces/{id}/groups   — create
# ─────────────────────────────────────────────────────────────────────────────

class WorkspaceDepartmentListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, workspace_id):
        workspace_id = _resolve_workspace_id_or_404(workspace_id)
        PermissionService.assert_workspace_section(workspace_id, request.user, 'departments')
        departments = DepartmentService.list_departments(workspace_id, request.user)
        return Response(WorkspaceDepartmentSerializer(departments, many=True).data)

    def post(self, request, workspace_id):
        workspace_id = _resolve_workspace_id_or_404(workspace_id)
        ser = DepartmentCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        department = DepartmentService.create_department(workspace_id, request.user, ser.validated_data)
        return Response(WorkspaceDepartmentSerializer(department).data, status=status.HTTP_201_CREATED)


class WorkspaceDepartmentDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, workspace_id, group_id):
        workspace_id = _resolve_workspace_id_or_404(workspace_id)
        ser = DepartmentUpdateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        department = DepartmentService.update_department(workspace_id, request.user, group_id, ser.validated_data)
        return Response(WorkspaceDepartmentSerializer(department).data)

    def delete(self, request, workspace_id, group_id):
        workspace_id = _resolve_workspace_id_or_404(workspace_id)
        DepartmentService.delete_department(workspace_id, request.user, group_id)
        return Response(status=status.HTTP_204_NO_CONTENT)


# ─────────────────────────────────────────────────────────────────────────────
# POST   /workspaces/{id}/groups/{group_id}/members      — add member
# DELETE /workspaces/{id}/groups/{group_id}/members/{uid}— remove member
# ─────────────────────────────────────────────────────────────────────────────

class WorkspaceDepartmentMemberView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, workspace_id, group_id):
        workspace_id = _resolve_workspace_id_or_404(workspace_id)
        ser = DepartmentMemberSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        user = _get_user_or_404(ser.validated_data['user_id'])
        gm = DepartmentService.add_member(workspace_id, request.user, group_id, user)
        return Response({'id': str(gm.pk), 'user_id': user.pk}, status=status.HTTP_201_CREATED)

    def delete(self, request, workspace_id, group_id, user_id):
        workspace_id = _resolve_workspace_id_or_404(workspace_id)
        target = _get_user_or_404(user_id)
        DepartmentService.remove_member(workspace_id, request.user, group_id, target)
        return Response(status=status.HTTP_204_NO_CONTENT)


WorkspaceGroupListView = WorkspaceDepartmentListView
WorkspaceGroupDetailView = WorkspaceDepartmentDetailView
WorkspaceGroupMemberView = WorkspaceDepartmentMemberView


# ─────────────────────────────────────────────────────────────────────────────
# GET  /workspaces/{id}/meetings    — list
# POST /workspaces/{id}/meetings    — create
# ─────────────────────────────────────────────────────────────────────────────

class WorkspaceMeetingListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, workspace_id):
        workspace_id = _resolve_workspace_id_or_404(workspace_id)
        PermissionService.assert_workspace_section(workspace_id, request.user, 'meetings')
        meetings = MeetingService.list_meetings(workspace_id, request.user)
        return Response(WorkspaceMeetingSerializer(meetings, many=True).data)

    def post(self, request, workspace_id):
        workspace_id = _resolve_workspace_id_or_404(workspace_id)
        ser = MeetingCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        meeting = MeetingService.create_meeting(workspace_id, request.user, ser.validated_data)
        return Response(WorkspaceMeetingSerializer(meeting).data, status=status.HTTP_201_CREATED)


# ─────────────────────────────────────────────────────────────────────────────
# PATCH  /workspaces/{id}/meetings/{meeting_id}  — update
# DELETE /workspaces/{id}/meetings/{meeting_id}  — cancel
# ─────────────────────────────────────────────────────────────────────────────

class WorkspaceMeetingDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, workspace_id, meeting_id):
        workspace_id = _resolve_workspace_id_or_404(workspace_id)
        ser = MeetingUpdateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        meeting = MeetingService.update_meeting(workspace_id, request.user, meeting_id, ser.validated_data)
        return Response(WorkspaceMeetingSerializer(meeting).data)

    def delete(self, request, workspace_id, meeting_id):
        workspace_id = _resolve_workspace_id_or_404(workspace_id)
        MeetingService.cancel_meeting(workspace_id, request.user, meeting_id)
        return Response(status=status.HTTP_204_NO_CONTENT)


# ─────────────────────────────────────────────────────────────────────────────
# GET  /workspaces/{id}/calendar/events     — list (optional ?start=&end=)
# POST /workspaces/{id}/calendar/events     — create
# ─────────────────────────────────────────────────────────────────────────────

class WorkspaceCalendarEventListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, workspace_id):
        workspace_id = _resolve_workspace_id_or_404(workspace_id)
        PermissionService.assert_workspace_section(workspace_id, request.user, 'calendar')
        start = request.query_params.get('start')
        end   = request.query_params.get('end')
        events = CalendarService.list_events(workspace_id, request.user, start, end)
        return Response(WorkspaceCalendarEventSerializer(events, many=True).data)

    def post(self, request, workspace_id):
        workspace_id = _resolve_workspace_id_or_404(workspace_id)
        ser = CalendarEventCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        event = CalendarService.create_event(workspace_id, request.user, ser.validated_data)
        return Response(WorkspaceCalendarEventSerializer(event).data, status=status.HTTP_201_CREATED)


# ─────────────────────────────────────────────────────────────────────────────
# PATCH  /workspaces/{id}/calendar/events/{event_id}
# DELETE /workspaces/{id}/calendar/events/{event_id}
# ─────────────────────────────────────────────────────────────────────────────

class WorkspaceCalendarEventDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, workspace_id, event_id):
        workspace_id = _resolve_workspace_id_or_404(workspace_id)
        ser = CalendarEventUpdateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        event = CalendarService.update_event(workspace_id, request.user, event_id, ser.validated_data)
        return Response(WorkspaceCalendarEventSerializer(event).data)

    def delete(self, request, workspace_id, event_id):
        workspace_id = _resolve_workspace_id_or_404(workspace_id)
        CalendarService.delete_event(workspace_id, request.user, event_id)
        return Response(status=status.HTTP_204_NO_CONTENT)


# ─────────────────────────────────────────────────────────────────────────────
# GET  /workspaces/{id}/files              — list root files (?folder_id=)
# POST /workspaces/{id}/files              — register upload
# ─────────────────────────────────────────────────────────────────────────────

class WorkspaceFileListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, workspace_id):
        workspace_id = _resolve_workspace_id_or_404(workspace_id)
        PermissionService.assert_workspace_section(workspace_id, request.user, 'files')
        folder_id = request.query_params.get('folder_id')
        files = FileService.list_files(workspace_id, request.user, folder_id)
        return Response(WorkspaceFileSerializer(files, many=True).data)

    def post(self, request, workspace_id):
        workspace_id = _resolve_workspace_id_or_404(workspace_id)
        ser = FileUploadSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        wf = FileService.upload_file(
            workspace_id, request.user,
            d.get('folder_id'), d['name'], d['content'], d.get('mime_type', '')
        )
        return Response(WorkspaceFileSerializer(wf).data, status=status.HTTP_201_CREATED)


# ─────────────────────────────────────────────────────────────────────────────
# DELETE /workspaces/{id}/files/{file_id}
# ─────────────────────────────────────────────────────────────────────────────

class WorkspaceFileDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, workspace_id, file_id):
        workspace_id = _resolve_workspace_id_or_404(workspace_id)
        content, workspace_file = FileService.download_file(workspace_id, request.user, file_id)
        response = FileResponse(content, content_type=workspace_file.mime_type or 'application/octet-stream')
        response['Content-Disposition'] = f'attachment; filename="{workspace_file.name}"'
        return response

    def delete(self, request, workspace_id, file_id):
        workspace_id = _resolve_workspace_id_or_404(workspace_id)
        FileService.delete_file(workspace_id, request.user, file_id)
        return Response(status=status.HTTP_204_NO_CONTENT)


# ─────────────────────────────────────────────────────────────────────────────
# GET  /workspaces/{id}/folders              — list folders (?parent_id=)
# POST /workspaces/{id}/folders              — create folder
# ─────────────────────────────────────────────────────────────────────────────

class WorkspaceFolderListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, workspace_id):
        workspace_id = _resolve_workspace_id_or_404(workspace_id)
        PermissionService.assert_workspace_section(workspace_id, request.user, 'files')
        parent_id = request.query_params.get('parent_id')
        folders = FileService.list_folders(workspace_id, request.user, parent_id)
        return Response(WorkspaceFolderSerializer(folders, many=True).data)

    def post(self, request, workspace_id):
        workspace_id = _resolve_workspace_id_or_404(workspace_id)
        ser = FolderCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        folder = FileService.create_folder(
            workspace_id, request.user,
            ser.validated_data.get('parent_id'), ser.validated_data['name']
        )
        return Response(WorkspaceFolderSerializer(folder).data, status=status.HTTP_201_CREATED)


# ─────────────────────────────────────────────────────────────────────────────
# GET   /workspaces/{id}/modules        — list
# PATCH /workspaces/{id}/modules        — enable/disable modules
# ─────────────────────────────────────────────────────────────────────────────

class WorkspaceModuleView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, workspace_id):
        workspace_id = _resolve_workspace_id_or_404(workspace_id)
        PermissionService.assert_workspace_section(workspace_id, request.user, 'permissions')
        from .models import WorkspaceModule
        modules = WorkspaceModule.objects.filter(workspace_id=workspace_id)
        return Response(WorkspaceModuleSerializer(modules, many=True).data)

    def patch(self, request, workspace_id):
        workspace_id = _resolve_workspace_id_or_404(workspace_id)
        ser = ModulesUpdateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        modules = SettingsService.update_modules(workspace_id, request.user, ser.validated_data)
        return Response(WorkspaceModuleSerializer(modules, many=True).data)


# ─────────────────────────────────────────────────────────────────────────────
# GET   /workspaces/{id}/settings       — get all settings
# PATCH /workspaces/{id}/settings       — update settings  { key: value, ... }
# ─────────────────────────────────────────────────────────────────────────────

class WorkspaceSettingsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, workspace_id):
        workspace_id = _resolve_workspace_id_or_404(workspace_id)
        PermissionService.assert_workspace_section(workspace_id, request.user, 'settings')
        settings = SettingsService.get_settings(workspace_id, request.user)
        return Response(settings)

    def patch(self, request, workspace_id):
        workspace_id = _resolve_workspace_id_or_404(workspace_id)
        if not isinstance(request.data, dict):
            return Response({'detail': 'Expected a JSON object.'}, status=status.HTTP_400_BAD_REQUEST)
        settings = SettingsService.update_settings(workspace_id, request.user, request.data)
        return Response(settings)


# ─────────────────────────────────────────────────────────────────────────────
# GET /workspaces/{id}/logs             — activity log (read-only)
# ─────────────────────────────────────────────────────────────────────────────

class WorkspaceLogView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, workspace_id):
        workspace_id = _resolve_workspace_id_or_404(workspace_id)
        PermissionService.assert_owner_or_admin(workspace_id, request.user)
        logs = WorkspaceLog.objects.filter(workspace_id=workspace_id).select_related('actor')[:200]
        return Response(WorkspaceLogSerializer(logs, many=True).data)


# ─────────────────────────────────────────────────────────────────────────────
# GET /workspaces/{id}/permissions/me   — current user's role & actions
# ─────────────────────────────────────────────────────────────────────────────

class WorkspaceMyPermissionsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, workspace_id):
        workspace_id = _resolve_workspace_id_or_404(workspace_id)
        summary = PermissionService.get_permission_summary(workspace_id, request.user)
        if summary is None:
            return Response({'detail': 'Not a member of this workspace.'}, status=status.HTTP_403_FORBIDDEN)
        return Response(summary)
