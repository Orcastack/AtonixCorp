import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('finances', '0025_automationartifact'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='PlatformAuditEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('workspace_id', models.UUIDField(blank=True, null=True)),
                ('domain', models.CharField(max_length=50)),
                ('event_type', models.CharField(max_length=100)),
                ('resource_type', models.CharField(max_length=100)),
                ('resource_id', models.CharField(max_length=100)),
                ('resource_name', models.CharField(blank=True, max_length=255)),
                ('summary', models.CharField(max_length=255)),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('search_text', models.TextField(blank=True)),
                ('occurred_at', models.DateTimeField(auto_now_add=True)),
                ('actor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='platform_audit_events', to=settings.AUTH_USER_MODEL)),
                ('entity', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='platform_audit_events', to='finances.entity')),
                ('organization', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='platform_audit_events', to='finances.organization')),
            ],
            options={
                'ordering': ['-occurred_at'],
            },
        ),
        migrations.CreateModel(
            name='PlatformTask',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('workspace_id', models.UUIDField(blank=True, null=True)),
                ('domain', models.CharField(default='platform', max_length=50)),
                ('task_type', models.CharField(max_length=100)),
                ('title', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True)),
                ('status', models.CharField(choices=[('open', 'Open'), ('in_progress', 'In Progress'), ('completed', 'Completed'), ('cancelled', 'Cancelled'), ('blocked', 'Blocked')], default='open', max_length=20)),
                ('priority', models.CharField(choices=[('low', 'Low'), ('normal', 'Normal'), ('high', 'High'), ('urgent', 'Urgent')], default='normal', max_length=20)),
                ('source_object_type', models.CharField(blank=True, max_length=100)),
                ('source_object_id', models.CharField(blank=True, max_length=100)),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('due_at', models.DateTimeField(blank=True, null=True)),
                ('started_at', models.DateTimeField(blank=True, null=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('assigned_to', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='assigned_platform_tasks', to=settings.AUTH_USER_MODEL)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_platform_tasks', to=settings.AUTH_USER_MODEL)),
                ('entity', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='platform_tasks', to='finances.entity')),
                ('organization', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='platform_tasks', to='finances.organization')),
            ],
            options={
                'ordering': ['status', '-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='platformauditevent',
            index=models.Index(fields=['domain', 'event_type'], name='fin_platf_domain_f9132d_idx'),
        ),
        migrations.AddIndex(
            model_name='platformauditevent',
            index=models.Index(fields=['organization', 'occurred_at'], name='fin_platf_organiz_5d93c2_idx'),
        ),
        migrations.AddIndex(
            model_name='platformauditevent',
            index=models.Index(fields=['workspace_id', 'occurred_at'], name='fin_platf_workspa_e265f7_idx'),
        ),
        migrations.AddIndex(
            model_name='platformauditevent',
            index=models.Index(fields=['resource_type', 'resource_id'], name='fin_platf_resourc_e836f1_idx'),
        ),
        migrations.AddIndex(
            model_name='platformtask',
            index=models.Index(fields=['domain', 'status'], name='fin_platf_domain_95f775_idx'),
        ),
        migrations.AddIndex(
            model_name='platformtask',
            index=models.Index(fields=['organization', 'status'], name='fin_platf_organiz_1cf804_idx'),
        ),
        migrations.AddIndex(
            model_name='platformtask',
            index=models.Index(fields=['workspace_id', 'status'], name='fin_platf_workspa_7ea255_idx'),
        ),
        migrations.AddIndex(
            model_name='platformtask',
            index=models.Index(fields=['assigned_to', 'status'], name='fin_platf_assigne_5f14f0_idx'),
        ),
        migrations.AddIndex(
            model_name='platformtask',
            index=models.Index(fields=['source_object_type', 'source_object_id'], name='fin_platf_source__60fca2_idx'),
        ),
    ]