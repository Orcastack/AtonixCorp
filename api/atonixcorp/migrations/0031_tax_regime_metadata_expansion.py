from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('finances', '0030_tax_regime_registry_global_tax_profile_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='taxregimeregistry',
            name='calculation_method',
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name='taxregimeregistry',
            name='penalty_rules',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name='taxregimeregistry',
            name='required_forms',
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name='taxregimeregistry',
            name='tax_type',
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name='taxprofile',
            name='effective_from',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='taxprofile',
            name='effective_to',
            field=models.DateField(blank=True, null=True),
        ),
    ]
