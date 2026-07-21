from django.db import migrations, models
import secrets


def backfill_secure_user_ids(apps, schema_editor):
    UserProfile = apps.get_model('finances', 'UserProfile')

    existing_ids = set(
        UserProfile.objects.exclude(secure_user_id__isnull=True)
        .exclude(secure_user_id='')
        .values_list('secure_user_id', flat=True)
    )

    for profile in UserProfile.objects.filter(models.Q(secure_user_id__isnull=True) | models.Q(secure_user_id='')):
        candidate = None
        while candidate is None or candidate in existing_ids:
            candidate = str(secrets.randbelow(9_000_000_000) + 1_000_000_000)
        profile.secure_user_id = candidate
        profile.save(update_fields=['secure_user_id'])
        existing_ids.add(candidate)


class Migration(migrations.Migration):

    dependencies = [
        ('finances', '0038_entity_workspace_mode_add_workspace'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='secure_user_id',
            field=models.CharField(blank=True, db_index=True, editable=False, max_length=10, unique=True),
        ),
        migrations.RunPython(backfill_secure_user_ids, migrations.RunPython.noop),
    ]