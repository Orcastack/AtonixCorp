from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('finances', '0034_tax_compliance_rules_and_frequency_expansion'),
    ]

    operations = [
        migrations.AddField(
            model_name='taxauditlog',
            name='country',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name='taxauditlog',
            name='device_metadata',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name='taxauditlog',
            name='previous_hash',
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AddField(
            model_name='taxauditlog',
            name='event_hash',
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.CreateModel(
            name='TaxRuleSetVersion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('version_number', models.CharField(max_length=40)),
                ('effective_from', models.DateField()),
                ('effective_to', models.DateField(blank=True, null=True)),
                ('change_log', models.JSONField(blank=True, default=list)),
                ('approval_status', models.CharField(choices=[('draft', 'Draft'), ('in_review', 'In Review'), ('approved', 'Approved'), ('rejected', 'Rejected'), ('deployed', 'Deployed'), ('expired', 'Expired')], default='draft', max_length=20)),
                ('approved_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('approved_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='approved_tax_rule_versions', to=settings.AUTH_USER_MODEL)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_tax_rule_versions', to=settings.AUTH_USER_MODEL)),
                ('registry', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='rule_versions', to='finances.taxregimeregistry')),
            ],
            options={
                'ordering': ['-effective_from', '-created_at'],
                'unique_together': {('registry', 'version_number')},
            },
        ),
        migrations.CreateModel(
            name='TaxRiskAlert',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('alert_type', models.CharField(choices=[('backdated_filing', 'Backdated Filing'), ('manipulated_tax_base', 'Manipulated Tax Base'), ('duplicate_filing', 'Duplicate Filing'), ('suspicious_rule_change', 'Suspicious Rule Change'), ('unauthorized_access', 'Unauthorized Access')], max_length=50)),
                ('severity', models.CharField(choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('critical', 'Critical')], default='medium', max_length=20)),
                ('title', models.CharField(max_length=255)),
                ('details', models.JSONField(blank=True, default=dict)),
                ('source_model', models.CharField(blank=True, max_length=120)),
                ('source_id', models.CharField(blank=True, max_length=120)),
                ('detected_at', models.DateTimeField(auto_now_add=True)),
                ('resolved_at', models.DateTimeField(blank=True, null=True)),
                ('entity', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tax_risk_alerts', to='finances.entity')),
                ('resolved_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='resolved_tax_risk_alerts', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-detected_at'],
            },
        ),
    ]
