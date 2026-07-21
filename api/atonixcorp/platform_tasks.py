from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .department_routing import apply_department_routing
from .models import PlatformTask
from .platform_foundation import log_platform_audit_event


ALLOWED_STATE_TRANSITIONS = {
    'open': {'in_progress', 'blocked', 'completed', 'cancelled'},
    'in_progress': {'blocked', 'completed', 'cancelled'},
    'blocked': {'in_progress', 'cancelled', 'completed'},
    'completed': set(),
    'cancelled': set(),
}


def _resolve_assignee(assignee_type, assignee_id):
    if assignee_type == 'user' and assignee_id:
        return get_object_or_404(User, id=assignee_id)
    return None


def _canonical_task_values(payload, *, actor=None):
    routed_payload = apply_department_routing(payload)
    state = routed_payload.get('state', routed_payload.get('status', 'open'))
    task_type = routed_payload.get('type', routed_payload.get('task_type', 'general'))
    assignee_type = routed_payload.get('assignee_type', 'user')
    assignee_id = str(routed_payload.get('assignee_id', routed_payload.get('assigned_to', '') or ''))
    origin_type = routed_payload.get('origin_type', routed_payload.get('source_object_type', ''))
    origin_id = str(routed_payload.get('origin_id', routed_payload.get('source_object_id', '') or ''))
    assigned_to = routed_payload.get('assigned_to') if isinstance(routed_payload.get('assigned_to'), User) else _resolve_assignee(assignee_type, assignee_id)

    return {
        'domain': routed_payload.get('domain', 'platform'),
        'task_type': task_type,
        'title': routed_payload.get('title', '').strip(),
        'description': routed_payload.get('description', ''),
        'status': state,
        'priority': routed_payload.get('priority', 'normal'),
        'assignee_type': assignee_type,
        'assignee_id': assignee_id,
        'assigned_to': assigned_to,
        'origin_type': origin_type,
        'origin_id': origin_id,
        'source_object_type': routed_payload.get('source_object_type', origin_type),
        'source_object_id': str(routed_payload.get('source_object_id', origin_id) or ''),
        'metadata': routed_payload.get('metadata', {}),
        'due_at': routed_payload.get('due_at'),
        'organization': routed_payload.get('organization'),
        'entity': routed_payload.get('entity'),
        'workspace_id': routed_payload.get('workspace_id'),
        'created_by': routed_payload.get('created_by', actor),
    }


def _validate_state_transition(current_state, next_state):
    if current_state == next_state:
        return
    if next_state not in ALLOWED_STATE_TRANSITIONS.get(current_state, set()):
        raise ValidationError({'state': f'Invalid task state transition: {current_state} -> {next_state}.'})


def create_task(payload, *, actor=None):
    values = _canonical_task_values(payload, actor=actor)
    if not values['title']:
        raise ValidationError({'title': 'Task title is required.'})
    task = PlatformTask.objects.create(**values)
    log_platform_audit_event(
        domain=task.domain,
        actor=actor,
        organization=task.organization,
        entity=task.entity,
        workspace_id=task.workspace_id,
        event_type='platform_task.created',
        action='task_created',
        resource_type='PlatformTask',
        resource_id=str(task.id),
        subject_type='task',
        subject_id=str(task.id),
        resource_name=task.title,
        summary=f'Created platform task: {task.title}',
        diff={'after': {'state': task.status, 'assignee_id': task.assignee_id, 'department_name': task.metadata.get('department_name'), 'cost_center': task.metadata.get('cost_center')}},
        context={'source_app': 'api'},
        metadata={'priority': task.priority, 'origin_type': task.origin_type, 'origin_id': task.origin_id, 'department_name': task.metadata.get('department_name'), 'cost_center': task.metadata.get('cost_center')},
    )
    return task


def update_task(task, payload, *, actor=None):
    before = {
        'state': task.status,
        'assignee_type': task.assignee_type,
        'assignee_id': task.assignee_id,
        'title': task.title,
        'priority': task.priority,
    }
    values = _canonical_task_values({
        'domain': payload.get('domain', task.domain),
        'type': payload.get('type', task.task_type),
        'title': payload.get('title', task.title),
        'description': payload.get('description', task.description),
        'state': payload.get('state', payload.get('status', task.status)),
        'priority': payload.get('priority', task.priority),
        'assignee_type': payload.get('assignee_type', task.assignee_type),
        'assignee_id': payload.get('assignee_id', task.assignee_id),
        'assigned_to': payload.get('assigned_to', task.assigned_to),
        'origin_type': payload.get('origin_type', task.origin_type),
        'origin_id': payload.get('origin_id', task.origin_id),
        'source_object_type': payload.get('source_object_type', task.source_object_type),
        'source_object_id': payload.get('source_object_id', task.source_object_id),
        'metadata': payload.get('metadata', task.metadata),
        'due_at': payload.get('due_at', task.due_at),
        'organization': payload.get('organization', task.organization),
        'entity': payload.get('entity', task.entity),
        'workspace_id': payload.get('workspace_id', task.workspace_id),
        'created_by': task.created_by,
    }, actor=actor)
    _validate_state_transition(task.status, values['status'])

    for field, value in values.items():
        setattr(task, field, value)
    if values['status'] == 'in_progress' and task.started_at is None:
        task.started_at = timezone.now()
    if values['status'] == 'completed' and task.completed_at is None:
        task.completed_at = timezone.now()
    task.save()

    after = {
        'state': task.status,
        'assignee_type': task.assignee_type,
        'assignee_id': task.assignee_id,
        'title': task.title,
        'priority': task.priority,
    }
    action = 'task_state_changed' if before['state'] != after['state'] else 'task_reassigned' if before['assignee_id'] != after['assignee_id'] else 'task_updated'
    log_platform_audit_event(
        domain=task.domain,
        actor=actor,
        organization=task.organization,
        entity=task.entity,
        workspace_id=task.workspace_id,
        event_type=f'platform_task.{action}',
        action=action,
        resource_type='PlatformTask',
        resource_id=str(task.id),
        subject_type='task',
        subject_id=str(task.id),
        resource_name=task.title,
        summary=f'Updated platform task: {task.title}',
        diff={'before': before, 'after': after},
        context={'source_app': 'api'},
        metadata={'origin_type': task.origin_type, 'origin_id': task.origin_id, 'department_name': task.metadata.get('department_name'), 'cost_center': task.metadata.get('cost_center')},
    )
    return task


def transition_task(task, next_state, *, actor=None, metadata_patch=None):
    payload = {'state': next_state, 'metadata': {**(task.metadata or {}), **(metadata_patch or {})}}
    return update_task(task, payload, actor=actor)