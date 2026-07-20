from datetime import timedelta

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from finances.models import Entity, Organization

from .models import WorkspaceGroup, WorkspaceMember
from .services import FINANCE_DEPARTMENT_TEMPLATES, WorkspaceService


class WorkspaceDepartmentAndMeetingAPITests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username='workspace-owner',
            email='workspace-owner@example.com',
            password='password123',
        )
        self.organization = Organization.objects.create(
            owner=self.owner,
            name='Workspace Org',
            slug='workspace-org',
            primary_country='US',
            primary_currency='USD',
        )
        self.entity = Entity.objects.create(
            organization=self.organization,
            name='Linked Entity',
            country='US',
            entity_type='corporation',
            status='active',
            local_currency='USD',
        )
        self.member = User.objects.create_user(
            username='workspace-member',
            email='workspace-member@example.com',
            password='password123',
        )
        self.workspace = WorkspaceService.create_workspace(
            self.owner,
            {'name': 'Workspace Ops', 'description': 'Testing workspace lifecycle'},
        )
        WorkspaceMember.objects.create(workspace=self.workspace, user=self.member, role='member')
        self.client.force_authenticate(self.owner)

    def test_workspace_is_seeded_with_default_departments(self):
        departments = list(
            WorkspaceGroup.objects.filter(workspace=self.workspace)
            .order_by('name')
            .values('name', 'cost_center', 'owner_id')
        )
        names = [department['name'] for department in departments]
        self.assertEqual(len(departments), len(FINANCE_DEPARTMENT_TEMPLATES))
        self.assertIn('Controllership', names)
        self.assertIn('Tax', names)
        self.assertTrue(all(department['cost_center'] for department in departments))
        self.assertTrue(all(department['owner_id'] == self.owner.id for department in departments))

    def test_department_can_be_created_updated_and_deleted(self):
        create_response = self.client.post(
            f'/api/v1/workspaces/{self.workspace.id}/departments',
            {
                'name': 'Board Review Office',
                'description': 'Quarterly review and governance department',
                'owner_user_id': self.member.id,
                'cost_center': 'FIN-BRD-999',
            },
            format='json',
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        group_id = create_response.data['id']
        self.assertEqual(create_response.data['owner']['id'], self.member.id)
        self.assertEqual(create_response.data['cost_center'], 'FIN-BRD-999')

        update_response = self.client.patch(
            f'/api/v1/workspaces/{self.workspace.id}/departments/{group_id}',
            {
                'name': 'Board Review Department',
                'description': 'Updated review department',
                'owner_user_id': self.owner.id,
                'cost_center': 'FIN-BRD-1000',
            },
            format='json',
        )
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        self.assertEqual(update_response.data['name'], 'Board Review Department')
        self.assertEqual(update_response.data['owner']['id'], self.owner.id)
        self.assertEqual(update_response.data['cost_center'], 'FIN-BRD-1000')

        delete_response = self.client.delete(f'/api/v1/workspaces/{self.workspace.id}/departments/{group_id}')
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)

    def test_workspace_can_link_to_entity_and_expose_it_via_api(self):
        update_response = self.client.patch(
            f'/api/v1/workspaces/{self.workspace.id}',
            {'linked_entity_id': self.entity.id},
            format='json',
        )
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        self.assertEqual(update_response.data['linked_entity_id'], self.entity.id)
        self.assertEqual(update_response.data['linked_entity_name'], 'Linked Entity')

    def test_entity_id_alias_resolves_workspace_members_endpoint(self):
        self.workspace.linked_entity = self.entity
        self.workspace.save(update_fields=['linked_entity'])

        response = self.client.get(f'/api/v1/workspaces/{self.entity.id}/members')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_meeting_can_be_created_updated_and_cancelled(self):
        start_at = timezone.now() + timedelta(days=2)
        end_at = start_at + timedelta(hours=1)
        create_response = self.client.post(
            f'/api/v1/workspaces/{self.workspace.id}/meetings',
            {
                'title': 'Quarterly Review',
                'description': 'Review capital plan',
                'start_at': start_at.isoformat(),
                'end_at': end_at.isoformat(),
            },
            format='json',
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        meeting_id = create_response.data['id']

        update_response = self.client.patch(
            f'/api/v1/workspaces/{self.workspace.id}/meetings/{meeting_id}',
            {'title': 'Quarterly Finance Review'},
            format='json',
        )
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        self.assertEqual(update_response.data['title'], 'Quarterly Finance Review')

        delete_response = self.client.delete(f'/api/v1/workspaces/{self.workspace.id}/meetings/{meeting_id}')
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)

    def test_file_and_folder_names_reject_path_traversal(self):
        folder_response = self.client.post(
            f'/api/v1/workspaces/{self.workspace.id}/folders',
            {'name': '../private'},
            format='json',
        )
        file_response = self.client.post(
            f'/api/v1/workspaces/{self.workspace.id}/files',
            {
                'name': 'folder/financials.pdf',
                'content': SimpleUploadedFile('financials.pdf', b'confidential report', content_type='application/pdf'),
                'mime_type': 'application/pdf',
            },
            format='multipart',
        )

        self.assertEqual(folder_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(file_response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_file_upload_download_encrypts_stored_content_and_is_audited(self):
        payload = b'confidential board material'
        upload_response = self.client.post(
            f'/api/v1/workspaces/{self.workspace.id}/files',
            {'content': SimpleUploadedFile('board-pack.pdf', payload, content_type='application/pdf')},
            format='multipart',
        )

        self.assertEqual(upload_response.status_code, status.HTTP_201_CREATED)
        download_response = self.client.get(
            f'/api/v1/workspaces/{self.workspace.id}/files/{upload_response.data["id"]}'
        )

        self.assertEqual(download_response.status_code, status.HTTP_200_OK)
        self.assertEqual(b''.join(download_response.streaming_content), payload)