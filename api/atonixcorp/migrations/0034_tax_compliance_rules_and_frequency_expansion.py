from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('finances', '0033_tax_regime_registry_json_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='taxregimeregistry',
            name='compliance_rules_json',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AlterField(
            model_name='taxregimeregistry',
            name='filing_frequency',
            field=models.CharField(choices=[('monthly', 'Monthly'), ('bi_monthly', 'Bi-Monthly'), ('quarterly', 'Quarterly'), ('semi_annual', 'Semi-Annual'), ('annual', 'Annual'), ('ad_hoc', 'Ad Hoc'), ('event_based', 'Event-Based')], default='annual', max_length=20),
        ),
        migrations.AlterField(
            model_name='taxfiling',
            name='submission_status',
            field=models.CharField(choices=[('draft', 'Draft'), ('in_progress', 'In Progress'), ('ready', 'Ready'), ('submitted', 'Submitted'), ('due_soon', 'Due Soon'), ('late', 'Late'), ('accepted', 'Accepted'), ('rejected', 'Rejected')], default='draft', max_length=20),
        ),
    ]
