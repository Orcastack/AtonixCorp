import uuid
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('finances', '0031_tax_regime_metadata_expansion'),
    ]

    operations = [
        migrations.AddField(
            model_name='taxcalculation',
            name='calculation_json',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name='taxcalculation',
            name='liability_amount',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=15),
        ),
        migrations.AddField(
            model_name='taxcalculation',
            name='period_end',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='taxcalculation',
            name='period_start',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='taxcalculation',
            name='status',
            field=models.CharField(default='draft', max_length=20),
        ),
        migrations.CreateModel(
            name='TaxFiling',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('tax_regime_code', models.CharField(max_length=80)),
                ('period_start', models.DateField()),
                ('period_end', models.DateField()),
                ('form_type', models.CharField(max_length=100)),
                ('form_json', models.JSONField(blank=True, default=dict)),
                ('submission_status', models.CharField(choices=[('draft', 'Draft'), ('ready', 'Ready'), ('submitted', 'Submitted'), ('accepted', 'Accepted'), ('rejected', 'Rejected')], default='draft', max_length=20)),
                ('submitted_at', models.DateTimeField(blank=True, null=True)),
                ('reference_number', models.CharField(blank=True, max_length=120)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('calculation', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='filings', to='finances.taxcalculation')),
                ('entity', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tax_filings', to='finances.entity')),
            ],
            options={
                'ordering': ['-created_at'],
                'unique_together': {('entity', 'tax_regime_code', 'period_start', 'period_end')},
            },
        ),
        migrations.CreateModel(
            name='TaxAuditLog',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('action_type', models.CharField(choices=[('create_profile', 'Create Profile'), ('update_profile', 'Update Profile'), ('calculate', 'Calculate'), ('file', 'File'), ('submit', 'Submit'), ('reconcile', 'Reconcile'), ('rule_change', 'Rule Change'), ('status_change', 'Status Change')], max_length=50)),
                ('old_value_json', models.JSONField(blank=True, default=dict)),
                ('new_value_json', models.JSONField(blank=True, default=dict)),
                ('reason', models.CharField(blank=True, max_length=255)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('entity', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tax_audit_logs', to='finances.entity')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='tax_audit_logs', to='auth.user')),
            ],
            options={
                'ordering': ['-timestamp'],
            },
        ),
    ]
