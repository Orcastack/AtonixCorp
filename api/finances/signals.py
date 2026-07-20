from django.db.models.signals import m2m_changed, post_delete, post_save
from django.dispatch import receiver

from .directory_service import sync_organization_directory
from .governance_configurations import refresh_governance_configuration
from .models import AutomationWorkflow, Entity, EntityDepartment, EntityRole, GovernancePolicy, Organization, TeamMember


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