from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('finances', '0032_tax_calculation_filing_and_audit_models'),
    ]

    operations = [
        migrations.AddField(
            model_name='taxregimeregistry',
            name='rules_json',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name='taxregimeregistry',
            name='forms_json',
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name='taxregimeregistry',
            name='penalty_rules_json',
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
