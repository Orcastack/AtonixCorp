from django.db import migrations, models
import django.db.models.deletion


def seed_rate_limit_profiles(apps, schema_editor):
    RateLimitProfile = apps.get_model('finances', 'RateLimitProfile')
    DeveloperAPI = apps.get_model('finances', 'DeveloperAPI')
    DeveloperPortalKeyRequest = apps.get_model('finances', 'DeveloperPortalKeyRequest')

    standard, _ = RateLimitProfile.objects.get_or_create(
        slug='standard',
        defaults={
            'name': 'STANDARD',
            'description': 'Default quota for public and sandbox developer access.',
            'requests_per_minute': 60,
            'requests_per_day': 10000,
            'is_default': True,
        },
    )
    partner, _ = RateLimitProfile.objects.get_or_create(
        slug='partner',
        defaults={
            'name': 'PARTNER',
            'description': 'Higher-throughput quota for approved institutional integrations.',
            'requests_per_minute': 300,
            'requests_per_day': 100000,
            'is_default': False,
        },
    )

    for api in DeveloperAPI.objects.filter(rate_limit_profile__isnull=True):
        api.rate_limit_profile = partner if api.access_level == 'partner' else standard
        api.save(update_fields=['rate_limit_profile'])

    DeveloperPortalKeyRequest.objects.filter(rate_limit_profile__isnull=True).update(rate_limit_profile=standard)


class Migration(migrations.Migration):

    dependencies = [
        ('finances', '0013_developer_portal_models'),
    ]

    operations = [
        migrations.CreateModel(
            name='RateLimitProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('slug', models.SlugField(unique=True)),
                ('description', models.TextField(blank=True)),
                ('requests_per_minute', models.PositiveIntegerField(default=60)),
                ('requests_per_day', models.PositiveIntegerField(default=10000)),
                ('is_default', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Rate Limit Profile',
                'verbose_name_plural': 'Rate Limit Profiles',
                'ordering': ['name'],
            },
        ),
        migrations.AddField(
            model_name='developerapi',
            name='rate_limit_profile',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='developer_apis', to='finances.ratelimitprofile'),
        ),
        migrations.AddField(
            model_name='developerportalkeyrequest',
            name='rate_limit_profile',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='developer_portal_key_requests', to='finances.ratelimitprofile'),
        ),
        migrations.CreateModel(
            name='DeveloperPortalAPILog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('method', models.CharField(max_length=10)),
                ('path', models.CharField(max_length=255)),
                ('status_code', models.PositiveIntegerField()),
                ('request_timestamp', models.DateTimeField()),
                ('response_time_ms', models.PositiveIntegerField(default=0)),
                ('client_ip', models.GenericIPAddressField(blank=True, null=True)),
                ('user_agent', models.TextField(blank=True)),
                ('source_metadata', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('api_service', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='portal_logs', to='finances.developerapi')),
                ('endpoint', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='portal_logs', to='finances.developerapiendpoint')),
                ('key_request', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='api_logs', to='finances.developerportalkeyrequest')),
                ('rate_limit_profile', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='portal_logs', to='finances.ratelimitprofile')),
            ],
            options={
                'verbose_name': 'Developer Portal API Log',
                'verbose_name_plural': 'Developer Portal API Logs',
                'ordering': ['-request_timestamp'],
            },
        ),
        migrations.AddIndex(
            model_name='developerportalapilog',
            index=models.Index(fields=['path', 'method'], name='finances_de_path_5d7d54_idx'),
        ),
        migrations.AddIndex(
            model_name='developerportalapilog',
            index=models.Index(fields=['request_timestamp'], name='finances_de_reques_d16d69_idx'),
        ),
        migrations.AddIndex(
            model_name='developerportalapilog',
            index=models.Index(fields=['status_code'], name='finances_de_status__4c8062_idx'),
        ),
        migrations.RunPython(seed_rate_limit_profiles, migrations.RunPython.noop),
    ]