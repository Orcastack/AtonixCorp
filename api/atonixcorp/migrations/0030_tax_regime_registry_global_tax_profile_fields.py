from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('finances', '0029_entity_holding_company_choice'),
    ]

    operations = [
        migrations.CreateModel(
            name='TaxRegimeRegistry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('jurisdiction_code', models.CharField(max_length=50)),
                ('country', models.CharField(max_length=100)),
                ('regime_code', models.CharField(max_length=80)),
                ('regime_name', models.CharField(max_length=255)),
                ('regime_category', models.CharField(choices=[('income_tax', 'Income Tax'), ('vat', 'VAT / GST / Sales Tax'), ('withholding', 'Withholding Tax'), ('payroll', 'Payroll Tax'), ('property', 'Property Tax'), ('customs', 'Customs / Duties'), ('other', 'Other')], default='other', max_length=30)),
                ('filing_frequency', models.CharField(choices=[('monthly', 'Monthly'), ('quarterly', 'Quarterly'), ('annual', 'Annual'), ('ad_hoc', 'Ad Hoc')], default='annual', max_length=20)),
                ('filing_form', models.CharField(blank=True, max_length=100)),
                ('effective_from', models.DateField(blank=True, null=True)),
                ('effective_to', models.DateField(blank=True, null=True)),
                ('rule_set', models.JSONField(blank=True, default=dict)),
                ('reference_links', models.JSONField(blank=True, default=list)),
                ('is_active', models.BooleanField(default=True)),
                ('notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['jurisdiction_code', 'regime_name'],
                'unique_together': {('jurisdiction_code', 'regime_code')},
            },
        ),
        migrations.AddField(
            model_name='taxprofile',
            name='jurisdiction_code',
            field=models.CharField(blank=True, default='', max_length=50),
        ),
        migrations.AddField(
            model_name='taxprofile',
            name='registered_regimes',
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name='taxprofile',
            name='registration_numbers',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name='taxprofile',
            name='filing_preferences',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name='taxcalculation',
            name='regime_code',
            field=models.CharField(blank=True, default='', max_length=80),
        ),
        migrations.AddField(
            model_name='taxcalculation',
            name='regime_name',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
    ]
