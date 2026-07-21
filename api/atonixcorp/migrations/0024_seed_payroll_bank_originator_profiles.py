from django.db import migrations


def seed_originator_profiles(apps, schema_editor):
    Entity = apps.get_model('finances', 'Entity')
    BankAccount = apps.get_model('finances', 'BankAccount')
    PayrollRun = apps.get_model('finances', 'PayrollRun')
    StaffPayrollProfile = apps.get_model('finances', 'StaffPayrollProfile')
    PayrollBankOriginatorProfile = apps.get_model('finances', 'PayrollBankOriginatorProfile')

    payroll_entity_ids = set(PayrollRun.objects.values_list('entity_id', flat=True))
    payroll_entity_ids.update(StaffPayrollProfile.objects.values_list('entity_id', flat=True))

    for entity in Entity.objects.filter(id__in=payroll_entity_ids).select_related('organization'):
        if PayrollBankOriginatorProfile.objects.filter(entity_id=entity.id).exists():
            continue

        bank_account = BankAccount.objects.filter(entity_id=entity.id).order_by('-is_active', 'id').first()
        identifier = (entity.registration_number or entity.organization.slug or f'ENTITY-{entity.id}')[:35]
        routing_or_sort = (bank_account.routing_number or '') if bank_account else ''
        sort_code = ''
        if entity.country.upper() == 'GB' and routing_or_sort:
            if len(routing_or_sort) == 6:
                sort_code = f'{routing_or_sort[0:2]}-{routing_or_sort[2:4]}-{routing_or_sort[4:6]}'
            elif len(routing_or_sort) >= 6:
                sort_code = f'{routing_or_sort[0:2]}-{routing_or_sort[2:4]}-{routing_or_sort[4:6]}'

        PayrollBankOriginatorProfile.objects.create(
            entity_id=entity.id,
            originator_name=entity.name[:255],
            originator_identifier=identifier,
            originating_bank_name=(bank_account.bank_name if bank_account and bank_account.bank_name else entity.main_bank)[:255],
            debit_account_name=(bank_account.account_name if bank_account else 'Payroll Operating')[:255],
            debit_account_number=(bank_account.account_number if bank_account else '')[:100],
            debit_routing_number=routing_or_sort[:50],
            debit_iban=(bank_account.iban if bank_account else '')[:34],
            debit_swift_code=(bank_account.swift_code if bank_account else '')[:11],
            debit_sort_code=sort_code[:20],
            company_entry_description='PAYROLL',
            company_discretionary_data=(entity.local_currency or '')[:20],
            initiating_party_name=entity.name[:255],
            initiating_party_identifier=identifier,
            is_active=True,
        )


class Migration(migrations.Migration):

    dependencies = [
        ('finances', '0023_payrollbankoriginatorprofile'),
    ]

    operations = [
        migrations.RunPython(seed_originator_profiles, migrations.RunPython.noop),
    ]