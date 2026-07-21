from django.db.models.signals import m2m_changed, post_delete, post_save, pre_save
from django.dispatch import receiver

from .directory_service import sync_organization_directory
from .governance_configurations import refresh_governance_configuration
from .models import AutomationWorkflow, Entity, EntityDepartment, EntityRole, GovernancePolicy, Organization, TeamMember
from .organization_email_service import send_system_notification


def _refresh(instance):
    if isinstance(instance, Organization):
        organization = instance
    elif isinstance(instance, (EntityDepartment, EntityRole)):
        try:
            organization = instance.entity.organization
        except Entity.DoesNotExist:
            return
    else:
        organization = instance.organization
    sync_organization_directory(organization)
    refresh_governance_configuration(organization)


@receiver(post_save, sender=Organization)
@receiver(post_save, sender=Entity)
@receiver(post_delete, sender=Entity)
@receiver(post_save, sender=EntityDepartment)
@receiver(post_delete, sender=EntityDepartment)
@receiver(post_save, sender=EntityRole)
@receiver(post_delete, sender=EntityRole)
@receiver(post_save, sender=TeamMember)
@receiver(post_delete, sender=TeamMember)
@receiver(post_save, sender=GovernancePolicy)
@receiver(post_delete, sender=GovernancePolicy)
@receiver(post_save, sender=AutomationWorkflow)
@receiver(post_delete, sender=AutomationWorkflow)
def refresh_governance_configuration_on_change(sender, instance, **kwargs):
    _refresh(instance)


@receiver(post_save, sender=Organization)
def send_organization_email_setup_notification(sender, instance, created, **kwargs):
    if not created:
        return
    send_system_notification(
        recipient=instance.owner.email,
        subject=f'{instance.name} workspace is ready',
        title='Organization setup confirmation',
        message=(
            f'{instance.name} has been created with registration identity '
            f'{instance.registration_number or "pending verification"}. Configure governance, team access, and email service from the organization console.'
        ),
        event_type='organization_created',
        organization=instance,
    )


@receiver(pre_save, sender=TeamMember)
def detect_team_member_role_change(sender, instance, update_fields=None, **kwargs):
    if not instance.pk or (update_fields is not None and 'role' not in update_fields):
        instance._email_role_changed = False
        return
    previous_role_id = sender.objects.filter(pk=instance.pk).values_list('role_id', flat=True).first()
    instance._email_role_changed = previous_role_id != instance.role_id


@receiver(post_save, sender=TeamMember)
def send_role_assignment_notification(sender, instance, created, **kwargs):
    if not (created or getattr(instance, '_email_role_changed', False)) or not instance.user.email:
        return
    role_name = instance.role.name if instance.role else 'Pending organization role'
    send_system_notification(
        recipient=instance.user.email,
        subject=f'Your role in {instance.organization.name}',
        title='Organization role assigned',
        message=f'You have been assigned the {role_name} role in {instance.organization.name}. Access remains subject to organization policy and acceptance status.',
        event_type='role_assignment',
        organization=instance.organization,
    )


@receiver(post_save, sender='workspaces.Workspace')
def send_workspace_created_notification(sender, instance, created, **kwargs):
    if not created or not instance.linked_entity_id or not instance.owner.email:
        return
    organization = instance.linked_entity.organization
    send_system_notification(
        recipient=instance.owner.email,
        subject=f'{instance.name} workspace is ready',
        title='Workspace created',
        message=f'{instance.name} is ready in {organization.name}. You can now configure members, departments, and workspace operations.',
        event_type='workspace_created',
        organization=organization,
    )


@receiver(m2m_changed, sender=EntityRole.permissions.through)
def refresh_governance_configuration_on_permission_change(sender, instance, action, **kwargs):
    if action in {'post_add', 'post_clear', 'post_remove'}:
        _refresh(instance)


@receiver(m2m_changed, sender=TeamMember.scoped_entities.through)
def refresh_directory_on_scope_change(sender, instance, action, **kwargs):
    if action in {'post_add', 'post_clear', 'post_remove'}:
        _refresh(instance)


@receiver(post_save, sender='workspaces.WorkspaceGroup')
@receiver(post_delete, sender='workspaces.WorkspaceGroup')
@receiver(post_save, sender='workspaces.Workspace')
@receiver(post_delete, sender='workspaces.Workspace')
def refresh_governance_configuration_on_workspace_group_change(sender, instance, **kwargs):
    entity = instance.linked_entity if sender._meta.model_name == 'workspace' else instance.workspace.linked_entity
    if entity:
        _refresh(entity)