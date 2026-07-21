from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('finances', '0039_userprofile_secure_user_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='entity',
            name='dashboard_config',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name='entity',
            name='hierarchy_metadata',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name='entity',
            name='industry',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name='entity',
            name='rbac_config',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name='entity',
            name='workspace_template_key',
            field=models.CharField(blank=True, default='', max_length=50),
        ),
        migrations.AddField(
            model_name='entity',
            name='workspace_type',
            field=models.CharField(blank=True, default='', max_length=50),
        ),
    ]