from django.db import migrations, models


def backfill_platform_foundation_fields(apps, schema_editor):
    PlatformAuditEvent = apps.get_model('finances', 'PlatformAuditEvent')
    PlatformTask = apps.get_model('finances', 'PlatformTask')

    for event in PlatformAuditEvent.objects.all().iterator():
        changed = False
        if event.actor_identifier is None:
            event.actor_identifier = ''
            changed = True
        if not event.subject_type:
            event.subject_type = event.resource_type or ''
            changed = True
        if not event.subject_id:
            event.subject_id = event.resource_id or ''
            changed = True
        if not event.action:
            event.action = event.event_type or ''
            changed = True
        if not event.actor_type:
            event.actor_type = 'user' if event.actor_id or event.actor_identifier else 'system'
            changed = True
        if event.actor_id and event.actor_identifier != str(event.actor_id):
            event.actor_identifier = str(event.actor_id)
            changed = True
        if event.context is None:
            event.context = {}
            changed = True
        if event.diff is None:
            event.diff = {}
            changed = True
        if event.metadata and not event.correlation_id:
            event.correlation_id = event.metadata.get('correlation_id', '') if isinstance(event.metadata, dict) else ''
            changed = True
        if changed:
            event.save(update_fields=['actor_type', 'actor_identifier', 'subject_type', 'subject_id', 'action', 'correlation_id', 'context', 'diff'])

    for task in PlatformTask.objects.all().iterator():
        changed = False
        if not task.assignee_type:
            task.assignee_type = 'user'
            changed = True
        if task.assigned_to_id and task.assignee_id != str(task.assigned_to_id):
            task.assignee_id = str(task.assigned_to_id)
            changed = True
        if not task.origin_type:
            task.origin_type = task.source_object_type or ''
            changed = True
        if not task.origin_id:
            task.origin_id = task.source_object_id or ''
            changed = True
        if changed:
            task.save(update_fields=['assignee_type', 'assignee_id', 'origin_type', 'origin_id'])


class Migration(migrations.Migration):

    dependencies = [
        ('finances', '0026_platform_audit_event_platform_task'),
    ]

    operations = [
        migrations.AddField(
            model_name='platformauditevent',
            name='action',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name='platformauditevent',
            name='actor_identifier',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name='platformauditevent',
            name='actor_type',
            field=models.CharField(choices=[('user', 'User'), ('system', 'System'), ('external', 'External')], default='user', max_length=20),
        ),
        migrations.AddField(
            model_name='platformauditevent',
            name='context',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name='platformauditevent',
            name='correlation_id',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name='platformauditevent',
            name='diff',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name='platformauditevent',
            name='subject_id',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name='platformauditevent',
            name='subject_type',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name='platformtask',
            name='assignee_id',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name='platformtask',
            name='assignee_type',
            field=models.CharField(choices=[('user', 'User'), ('role', 'Role'), ('group', 'Group')], default='user', max_length=20),
        ),
        migrations.AddField(
            model_name='platformtask',
            name='origin_id',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name='platformtask',
            name='origin_type',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddIndex(
            model_name='platformauditevent',
            index=models.Index(fields=['subject_type', 'subject_id'], name='fin_platf_subject_e6bf86_idx'),
        ),
        migrations.AddIndex(
            model_name='platformauditevent',
            index=models.Index(fields=['actor_identifier', 'occurred_at'], name='fin_platf_actor_i_c9c1f4_idx'),
        ),
        migrations.AddIndex(
            model_name='platformauditevent',
            index=models.Index(fields=['action', 'occurred_at'], name='fin_platf_action__8d5bfe_idx'),
        ),
        migrations.AddIndex(
            model_name='platformauditevent',
            index=models.Index(fields=['correlation_id'], name='fin_platf_correla_ef4ef2_idx'),
        ),
        migrations.AddIndex(
            model_name='platformtask',
            index=models.Index(fields=['origin_type', 'origin_id'], name='fin_platf_origin__f69369_idx'),
        ),
        migrations.AddIndex(
            model_name='platformtask',
            index=models.Index(fields=['assignee_type', 'assignee_id'], name='fin_platf_assigne_5dc19d_idx'),
        ),
        migrations.RunPython(backfill_platform_foundation_fields, migrations.RunPython.noop),
    ]