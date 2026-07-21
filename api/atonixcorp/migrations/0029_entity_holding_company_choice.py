from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('finances', '0028_rename_platform_foundation_indexes'),
    ]

    operations = [
        migrations.AlterField(
            model_name='entity',
            name='entity_type',
            field=models.CharField(
                choices=[
                    ('sole_proprietor', 'Sole Proprietor'),
                    ('llc', 'LLC'),
                    ('partnership', 'Partnership'),
                    ('corporation', 'Corporation'),
                    ('holding_company', 'Holding Company'),
                    ('nonprofit', 'Nonprofit'),
                    ('subsidiary', 'Subsidiary'),
                    ('branch', 'Branch'),
                    ('other', 'Other'),
                ],
                max_length=50,
            ),
        ),
    ]