from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('finances', '0037_remove_entity_unique_together'),
    ]

    operations = [
        migrations.AlterField(
            model_name='entity',
            name='workspace_mode',
            field=models.CharField(
                max_length=20,
                choices=[
                    ('accounting', 'Accounting'),
                    ('equity', 'Equity'),
                    ('combined', 'Combined'),
                    ('standalone', 'Standalone'),
                    ('workspace', 'Workspace'),
                ],
                default='accounting',
            ),
        ),
    ]
