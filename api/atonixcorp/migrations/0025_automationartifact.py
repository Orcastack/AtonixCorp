from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('finances', '0024_seed_payroll_bank_originator_profiles'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AutomationArtifact',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('artifact_type', models.CharField(choices=[('enterprise_board_pack', 'Enterprise Board Pack'), ('compliance_board_pack', 'Compliance Board Pack')], default='enterprise_board_pack', max_length=50)),
                ('export_format', models.CharField(default='pdf', max_length=10)),
                ('file_name', models.CharField(max_length=255)),
                ('file_path', models.FileField(upload_to='automation_artifacts/%Y/%m/%d/')),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('entity', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='automation_artifacts', to='finances.entity')),
                ('execution', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='artifacts', to='finances.automationexecution')),
                ('generated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('organization', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='automation_artifacts', to='finances.organization')),
                ('workflow', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='artifacts', to='finances.automationworkflow')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]