from decimal import Decimal
from io import StringIO
import csv

from django.db import transaction as db_transaction
from django.utils import timezone

from .accounting_controls import ensure_period_is_open
from .models import (
    ChartOfAccounts,
    EntityStaff,
    GeneralLedger,
    JournalEntry,
    LeaveBalance,
    LeaveRequest,
    LeaveType,
    PayrollBankPaymentFile,
    PayrollBankOriginatorProfile,
    PayrollRun,
    PayrollStatutoryReport,
    Payslip,
    PayslipLineItem,
    StaffPayrollProfile,
)
from .payroll_bank_exports import resolve_bank_export_scheme, validate_bank_export_profiles
from .payroll_presets import (
    get_payroll_country_preset,
    resolve_bank_export_variant,
    resolve_bank_file_format,
    resolve_bank_institution,
)


DECIMAL_ZERO = Decimal('0.00')
TWOPLACES = Decimal('0.01')
FOURPLACES = Decimal('0.0001')
PERIODS_PER_YEAR = {
    'weekly': Decimal('52'),
    'biweekly': Decimal('26'),
    'semimonthly': Decimal('24'),
    'monthly': Decimal('12'),
}


def _amount(value):
    return Decimal(str(value or 0)).quantize(TWOPLACES)


def _rate(value):
    return Decimal(str(value or 0)).quantize(FOURPLACES)


def _make_reference(prefix, payroll_run_id, suffix=''):
    core = f'{prefix}-{payroll_run_id}'
    if suffix:
        core = f'{core}-{suffix}'
    return core[:100]


def _country_code_for_payroll(payroll_run):
    return payroll_run.entity.country or payroll_run.organization.primary_country or ''


def _effective_profile_preset(profile, entity):
    preset = get_payroll_country_preset(entity.country)
    return {
        'income_tax_rate': profile.income_tax_rate if profile and profile.income_tax_rate is not None else preset['income_tax_rate'],
        'employee_tax_rate': profile.employee_tax_rate if profile and profile.employee_tax_rate is not None else preset['employee_tax_rate'],
        'employer_tax_rate': profile.employer_tax_rate if profile and profile.employer_tax_rate is not None else preset['employer_tax_rate'],
        'bank_file_format': preset['bank_file_format'],
        'statutory_jurisdiction': (profile.statutory_jurisdiction if profile and profile.statutory_jurisdiction else preset['statutory_jurisdiction']),
    }


def estimate_payroll_run_amount(payroll_run):
    total = DECIMAL_ZERO
    staff_members = EntityStaff.objects.filter(
        entity=payroll_run.entity,
        status='active',
    ).select_related('payroll_profile').prefetch_related('payroll_component_assignments__component')

    for staff_member in staff_members:
        profile = getattr(staff_member, 'payroll_profile', None)
        if profile and not profile.is_active:
            profile = None
        base_period_salary = _period_salary(staff_member, profile, profile.pay_frequency if profile else payroll_run.pay_frequency)
        if base_period_salary <= DECIMAL_ZERO:
            continue
        gross_pay = base_period_salary
        deductions_total = DECIMAL_ZERO
        assignments = [
            assignment for assignment in staff_member.payroll_component_assignments.all()
            if assignment.is_active
            and (not assignment.effective_start or assignment.effective_start <= payroll_run.period_end)
            and (not assignment.effective_end or assignment.effective_end >= payroll_run.period_start)
        ]
        for assignment in assignments:
            amount = _component_amount(assignment, base_period_salary)
            if amount <= DECIMAL_ZERO:
                continue
            component = assignment.component
            if component.component_type in {'earning', 'benefit'} and not component.employer_contribution:
                gross_pay += amount
            elif component.component_type == 'deduction':
                deductions_total += amount
        total += gross_pay - deductions_total
    return total.quantize(TWOPLACES)


def _find_or_create_account(entity, code, name, account_type):
    account, _ = ChartOfAccounts.objects.get_or_create(
        entity=entity,
        account_code=code,
        defaults={
            'account_name': name,
            'account_type': account_type,
            'currency': entity.local_currency,
            'status': 'active',
        },
    )
    return account


def _payroll_accounts(entity):
    return {
        'salary_expense': _find_or_create_account(entity, '6100', 'Payroll Salary Expense', 'expense'),
        'benefits_expense': _find_or_create_account(entity, '6110', 'Payroll Benefits Expense', 'expense'),
        'employer_tax_expense': _find_or_create_account(entity, '6120', 'Employer Payroll Tax Expense', 'expense'),
        'payroll_payable': _find_or_create_account(entity, '2100', 'Payroll Payable', 'liability'),
        'withholding_liability': _find_or_create_account(entity, '2110', 'Payroll Tax Withholding Liability', 'liability'),
        'deduction_liability': _find_or_create_account(entity, '2120', 'Payroll Deductions Liability', 'liability'),
        'employer_tax_liability': _find_or_create_account(entity, '2130', 'Employer Payroll Tax Liability', 'liability'),
        'benefits_payable': _find_or_create_account(entity, '2140', 'Employer Benefits Payable', 'liability'),
        'payroll_cash': _find_or_create_account(entity, '1010', 'Payroll Cash Clearing', 'asset'),
    }


def _period_salary(staff_member, payroll_profile, pay_frequency):
    salary_basis = 'annual'
    base_salary = None
    if payroll_profile and payroll_profile.is_active:
        salary_basis = payroll_profile.salary_basis
        base_salary = payroll_profile.base_salary
    if base_salary is None:
        base_salary = staff_member.salary
    if base_salary is None:
        return DECIMAL_ZERO

    base_salary = _amount(base_salary)
    periods = PERIODS_PER_YEAR.get(pay_frequency or 'monthly', Decimal('12'))
    if salary_basis == 'monthly':
        return (base_salary * Decimal('12') / periods).quantize(TWOPLACES)
    return (base_salary / periods).quantize(TWOPLACES)


def _component_amount(assignment, base_amount):
    component = assignment.component
    raw_value = assignment.amount_override if assignment.amount_override is not None else component.amount
    raw_value = _amount(raw_value)
    if component.calculation_type == 'percent_of_base':
        return (base_amount * raw_value / Decimal('100')).quantize(TWOPLACES)
    return raw_value


def _process_leave_for_staff(staff_member, payroll_run):
    accrued_total = DECIMAL_ZERO
    used_total = DECIMAL_ZERO
    ending_balance = DECIMAL_ZERO

    balances = list(LeaveBalance.objects.filter(
        staff_member=staff_member,
        leave_type__is_active=True,
    ).select_related('leave_type'))

    existing_leave_type_ids = {balance.leave_type_id for balance in balances}
    for leave_type in LeaveType.objects.filter(entity=staff_member.entity, is_active=True).exclude(id__in=existing_leave_type_ids):
        balances.append(LeaveBalance.objects.create(staff_member=staff_member, leave_type=leave_type))

    requests = LeaveRequest.objects.filter(
        staff_member=staff_member,
        status='approved',
        payroll_run__isnull=True,
        start_date__lte=payroll_run.period_end,
        end_date__gte=payroll_run.period_start,
    ).select_related('leave_type')

    request_by_type = {}
    for request in requests:
        request_by_type.setdefault(request.leave_type_id, []).append(request)

    for balance in balances:
        leave_type = balance.leave_type
        accrual = _amount(leave_type.accrual_hours_per_run)
        new_accrued = _amount(balance.accrued_hours) + accrual

        if leave_type.max_balance_hours:
            max_balance = _amount(leave_type.max_balance_hours)
            current_after = _amount(balance.opening_balance_hours) + new_accrued - _amount(balance.used_hours)
            if current_after > max_balance:
                new_accrued -= current_after - max_balance
                if new_accrued < DECIMAL_ZERO:
                    new_accrued = DECIMAL_ZERO
                accrual = new_accrued - _amount(balance.accrued_hours)

        used_for_type = DECIMAL_ZERO
        for request in request_by_type.get(leave_type.id, []):
            used_for_type += _amount(request.hours_requested)
            request.status = 'processed'
            request.payroll_run = payroll_run
            request.save(update_fields=['status', 'payroll_run', 'updated_at'])
        balance.accrued_hours = new_accrued
        balance.used_hours = _amount(balance.used_hours) + used_for_type
        balance.save(update_fields=['accrued_hours', 'used_hours', 'updated_at'])

        accrued_total += accrual
        used_total += used_for_type
        ending_balance += _amount(balance.current_balance_hours)

    return accrued_total.quantize(TWOPLACES), used_total.quantize(TWOPLACES), ending_balance.quantize(TWOPLACES)


def _create_journal_entry(payroll_run, acting_user, totals):
    accounts = _payroll_accounts(payroll_run.entity)
    reference = _make_reference('PR-JE', payroll_run.id)
    journal_entry = JournalEntry.objects.create(
        entity=payroll_run.entity,
        entry_type='automated',
        reference_number=reference,
        description=f'Payroll run {payroll_run.name}',
        posting_date=payroll_run.payment_date,
        memo='Automatically generated by the payroll engine.',
        amount_total=totals['debit_total'],
        status='posted',
        created_by=acting_user,
        approved_by=acting_user,
        approved_at=timezone.now(),
        submitted_at=timezone.now(),
    )

    entries = []
    if totals['gross_pay_total'] > DECIMAL_ZERO:
        entries.append((accounts['salary_expense'], accounts['payroll_payable'], totals['gross_pay_total'], 'Payroll gross pay'))
    if totals['employer_benefits_total'] > DECIMAL_ZERO:
        entries.append((accounts['benefits_expense'], accounts['benefits_payable'], totals['employer_benefits_total'], 'Employer payroll benefits'))
    if totals['tax_withholding_total'] > DECIMAL_ZERO:
        entries.append((accounts['payroll_payable'], accounts['withholding_liability'], totals['tax_withholding_total'], 'Employee tax withholding'))
    if totals['deductions_total'] > DECIMAL_ZERO:
        entries.append((accounts['payroll_payable'], accounts['deduction_liability'], totals['deductions_total'], 'Employee payroll deductions'))
    if totals['employer_tax_total'] > DECIMAL_ZERO:
        entries.append((accounts['employer_tax_expense'], accounts['employer_tax_liability'], totals['employer_tax_total'], 'Employer payroll taxes'))
    if totals['net_pay_total'] > DECIMAL_ZERO:
        entries.append((accounts['payroll_payable'], accounts['payroll_cash'], totals['net_pay_total'], 'Net pay settled through payment file'))

    for debit_account, credit_account, amount, description in entries:
        if amount <= DECIMAL_ZERO:
            continue
        GeneralLedger.objects.create(
            entity=payroll_run.entity,
            debit_account=debit_account,
            credit_account=credit_account,
            debit_amount=amount,
            credit_amount=amount,
            description=description,
            reference_number=reference,
            posting_date=payroll_run.payment_date,
            journal_entry=journal_entry,
            posting_status='posted',
        )

    return journal_entry


def _statutory_report_payload(payroll_run):
    jurisdiction = payroll_run.entity.country or payroll_run.organization.primary_country or 'Unknown'
    base_payload = {
        'entity': payroll_run.entity.name,
        'period_start': payroll_run.period_start.isoformat(),
        'period_end': payroll_run.period_end.isoformat(),
        'payment_date': payroll_run.payment_date.isoformat(),
        'employee_count': payroll_run.employee_count,
        'gross_pay_total': str(payroll_run.gross_pay_total),
        'employee_benefits_total': str(payroll_run.employee_benefits_total),
        'employer_benefits_total': str(payroll_run.employer_benefits_total),
        'deductions_total': str(payroll_run.deductions_total),
        'tax_withholding_total': str(payroll_run.tax_withholding_total),
        'employer_tax_total': str(payroll_run.employer_tax_total),
        'net_pay_total': str(payroll_run.net_pay_total),
    }
    return jurisdiction, base_payload


def _sanitize_fixed_width(value, length):
    return str(value or '')[:length].ljust(length)


def _sanitize_numeric(value, length):
    digits = ''.join(ch for ch in str(value or '') if ch.isdigit())
    return digits[:length].rjust(length, '0')


def _amount_in_cents(value, length=10):
    return str(int((value or DECIMAL_ZERO) * 100)).rjust(length, '0')


def _build_wells_fargo_ppd_content(payroll_run, originator_profile, payslips, scheme):
    header = ''.join([
        'WFPPD',
        _sanitize_fixed_width(originator_profile.originator_name, 23),
        _sanitize_fixed_width(originator_profile.originator_identifier, 10),
        _sanitize_fixed_width(originator_profile.company_entry_description or 'PAYROLL', 10),
        _sanitize_fixed_width(originator_profile.company_discretionary_data, 20),
        payroll_run.payment_date.strftime('%Y%m%d'),
        str(len(payslips)).rjust(6, '0'),
    ])
    details = []
    total = DECIMAL_ZERO
    for sequence, payslip in enumerate(payslips, start=1):
        profile = payslip.payroll_profile
        total += payslip.net_pay or DECIMAL_ZERO
        details.append(''.join([
            '6',
            _sanitize_numeric(profile.default_bank_routing_number if profile else '', 9),
            _sanitize_numeric(profile.default_bank_account_number if profile else '', 17),
            _amount_in_cents(payslip.net_pay, 10),
            _sanitize_fixed_width(payslip.staff_member.full_name, 22),
            _sanitize_fixed_width((payslip.bank_payment_reference or '')[:scheme['reference_max_length']], 10),
            str(sequence).rjust(7, '0'),
        ]))
    control = ''.join([
        '8',
        _sanitize_numeric(originator_profile.debit_routing_number, 9),
        _sanitize_numeric(originator_profile.debit_account_number, 17),
        _amount_in_cents(total, 12),
        str(len(payslips)).rjust(6, '0'),
    ])
    return '\n'.join([header, *details, control])


def _build_chase_ppd_content(payroll_run, originator_profile, payslips, scheme):
    lines = [
        ','.join([
            'CHASEHDR',
            payroll_run.payment_date.strftime('%Y%m%d'),
            _sanitize_fixed_width(originator_profile.originator_name, 23).strip(),
            _sanitize_fixed_width(originator_profile.originator_identifier, 12).strip(),
            _sanitize_fixed_width(originator_profile.company_entry_description or 'PAYROLL', 10).strip(),
            str(len(payslips)),
        ])
    ]
    total = DECIMAL_ZERO
    for payslip in payslips:
        profile = payslip.payroll_profile
        total += payslip.net_pay or DECIMAL_ZERO
        lines.append(','.join([
            'CHASEDTL',
            _sanitize_numeric(profile.default_bank_routing_number if profile else '', 9),
            _sanitize_numeric(profile.default_bank_account_number if profile else '', 17),
            _amount_in_cents(payslip.net_pay, 10),
            _sanitize_fixed_width(payslip.staff_member.full_name, 22).strip(),
            _sanitize_fixed_width((payslip.bank_payment_reference or '')[:scheme['reference_max_length']], 12).strip(),
        ]))
    lines.append(','.join([
        'CHASECTL',
        _sanitize_numeric(originator_profile.debit_routing_number, 9),
        _sanitize_numeric(originator_profile.debit_account_number, 17),
        _amount_in_cents(total, 12),
        str(len(payslips)),
    ]))
    return '\n'.join(lines)


def _build_sepa_content(payroll_run, originator_profile, payslips, scheme):
    rows = []
    for index, payslip in enumerate(payslips, start=1):
        profile = payslip.payroll_profile
        rows.append(
            f"<CdtTrfTxInf><PmtId><InstrId>PMT-{payroll_run.id}-{index}</InstrId><EndToEndId>{(payslip.bank_payment_reference or '')[:scheme['reference_max_length']]}</EndToEndId></PmtId><Amt><InstdAmt Ccy=\"{payroll_run.entity.local_currency}\">{payslip.net_pay}</InstdAmt></Amt><CdtrAgt><FinInstnId><BIC>{(profile.default_bank_swift_code if profile else '')}</BIC></FinInstnId></CdtrAgt><Cdtr><Nm>{payslip.staff_member.full_name}</Nm></Cdtr><CdtrAcct><Id><IBAN>{(profile.default_bank_iban if profile else '')}</IBAN></Id></CdtrAcct><RmtInf><Ustrd>{(payslip.bank_payment_reference or '')[:scheme['reference_max_length']]}</Ustrd></RmtInf></CdtTrfTxInf>"
        )
    total = sum((payslip.net_pay or DECIMAL_ZERO) for payslip in payslips)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<Document xmlns="{scheme.get("xml_namespace", "urn:iso:std:iso:20022:tech:xsd:pain.001.001.03")}">'
        '<CstmrCdtTrfInitn>'
        f'<GrpHdr><MsgId>PAYROLL-{payroll_run.id}</MsgId><CreDtTm>{timezone.now().strftime("%Y-%m-%dT%H:%M:%S")}</CreDtTm><NbOfTxs>{len(payslips)}</NbOfTxs><CtrlSum>{total}</CtrlSum><InitgPty><Nm>{originator_profile.initiating_party_name or originator_profile.originator_name}</Nm><Id><OrgId><Othr><Id>{originator_profile.initiating_party_identifier or originator_profile.originator_identifier or f"PAYROLL-{payroll_run.entity_id}"}</Id></Othr></OrgId></Id></InitgPty></GrpHdr>'
        f'<PmtInf><PmtInfId>PAYROLL-{payroll_run.id}</PmtInfId><PmtMtd>TRF</PmtMtd><BtchBookg>true</BtchBookg><NbOfTxs>{len(payslips)}</NbOfTxs><CtrlSum>{total}</CtrlSum><PmtTpInf><SvcLvl><Cd>SEPA</Cd></SvcLvl></PmtTpInf><ReqdExctnDt>{payroll_run.payment_date.isoformat()}</ReqdExctnDt><Dbtr><Nm>{originator_profile.originator_name}</Nm></Dbtr><DbtrAcct><Id><IBAN>{originator_profile.debit_iban}</IBAN></Id></DbtrAcct><DbtrAgt><FinInstnId><BIC>{originator_profile.debit_swift_code}</BIC></FinInstnId></DbtrAgt><ChrgBr>SLEV</ChrgBr>{"".join(rows)}</PmtInf>'
        '</CstmrCdtTrfInitn>'
        '</Document>'
    )


def _build_barclays_bacs_content(originator_profile, payslips, scheme):
    lines = [
        ''.join([
            'BH',
            _sanitize_fixed_width(originator_profile.originator_name, 18),
            _sanitize_fixed_width(originator_profile.originator_identifier, 6),
            _sanitize_fixed_width(originator_profile.debit_account_name, 18),
            _sanitize_numeric(originator_profile.debit_account_number, 8),
            _sanitize_numeric(originator_profile.debit_sort_code, 6),
        ])
    ]
    total = DECIMAL_ZERO
    for payslip in payslips:
        profile = payslip.payroll_profile
        total += payslip.net_pay or DECIMAL_ZERO
        lines.append(''.join([
            'BD',
            _sanitize_fixed_width(profile.default_bank_account_name if profile else '', 18),
            _sanitize_numeric(profile.default_bank_account_number if profile else '', 8),
            _sanitize_numeric(profile.default_bank_sort_code if profile else '', 6),
            _amount_in_cents(payslip.net_pay, 11),
            _sanitize_fixed_width((payslip.bank_payment_reference or '')[:scheme['reference_max_length']], 18),
        ]))
    lines.append(''.join(['BT', _amount_in_cents(total, 13), str(len(payslips)).rjust(6, '0')]))
    return '\n'.join(lines)


def _build_hsbc_bacs_content(originator_profile, payslips, scheme):
    lines = [
        ','.join([
            'HSBCBH',
            _sanitize_fixed_width(originator_profile.originator_name, 18).strip(),
            _sanitize_fixed_width(originator_profile.originator_identifier, 10).strip(),
            _sanitize_fixed_width(originator_profile.debit_account_name, 18).strip(),
            _sanitize_numeric(originator_profile.debit_account_number, 8),
            _sanitize_numeric(originator_profile.debit_sort_code, 6),
        ])
    ]
    total = DECIMAL_ZERO
    for payslip in payslips:
        profile = payslip.payroll_profile
        total += payslip.net_pay or DECIMAL_ZERO
        lines.append(','.join([
            'HSBCBD',
            _sanitize_fixed_width(profile.default_bank_account_name if profile else '', 18).strip(),
            _sanitize_numeric(profile.default_bank_account_number if profile else '', 8),
            _sanitize_numeric(profile.default_bank_sort_code if profile else '', 6),
            _amount_in_cents(payslip.net_pay, 11),
            _sanitize_fixed_width((payslip.bank_payment_reference or '')[:scheme['reference_max_length']], 18).strip(),
        ]))
    lines.append(','.join(['HSBCBT', _amount_in_cents(total, 13), str(len(payslips)).rjust(6, '0')]))
    return '\n'.join(lines)


def _build_adp_workforce_now_content(originator_profile, payslips, scheme):
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow([
        'company_code', 'company_name', 'debit_account_number', 'employee_id', 'employee_name',
        'account_type', 'account_name', 'account_number', 'amount_cents', 'reference',
    ])
    company_code = (originator_profile.originator_identifier or f'PAYROLL-{originator_profile.entity_id}')[:20]
    for payslip in payslips:
        profile = payslip.payroll_profile
        writer.writerow([
            company_code,
            originator_profile.originator_name[:40],
            originator_profile.debit_account_number,
            payslip.staff_member.employee_id,
            payslip.staff_member.full_name[:35],
            'CHECKING',
            (profile.default_bank_account_name if profile else '')[:35],
            profile.default_bank_account_number if profile else '',
            _amount_in_cents(payslip.net_pay, 10),
            (payslip.bank_payment_reference or '')[:scheme['reference_max_length']],
        ])
    return buffer.getvalue()


def _generate_statutory_reports(payroll_run):
    jurisdiction, payload = _statutory_report_payload(payroll_run)
    due_date = payroll_run.payment_date
    reports = [
        ('payroll_register', payload),
        ('withholding_return', {**payload, 'withholding_due': str(payroll_run.tax_withholding_total)}),
        ('social_contribution', {**payload, 'employer_contribution_due': str(payroll_run.employer_tax_total)}),
    ]
    PayrollStatutoryReport.objects.filter(payroll_run=payroll_run).delete()
    for report_type, report_payload in reports:
        PayrollStatutoryReport.objects.create(
            payroll_run=payroll_run,
            report_type=report_type,
            jurisdiction=jurisdiction,
            due_date=due_date,
            report_payload=report_payload,
        )


def _generate_bank_payment_file(payroll_run):
    payslips = list(payroll_run.payslips.select_related('staff_member', 'payroll_profile').order_by('staff_member__last_name'))
    originator_profile = getattr(payroll_run.entity, 'payroll_bank_originator_profile', None)
    country_code = _country_code_for_payroll(payroll_run)
    file_format = resolve_bank_file_format(country_code, payroll_run.requested_bank_file_format)
    institution_code = resolve_bank_institution(country_code, payroll_run.requested_bank_institution)
    variant_code = resolve_bank_export_variant(country_code, payroll_run.requested_bank_export_variant)
    scheme = resolve_bank_export_scheme(file_format, institution_code, variant_code)
    validate_bank_export_profiles(payslips, originator_profile, scheme)

    if file_format == 'aba':
        if scheme['institution_code'] == 'wells_fargo' and scheme['variant_code'] == 'ppd':
            content = _build_wells_fargo_ppd_content(payroll_run, originator_profile, payslips, scheme)
        elif scheme['institution_code'] == 'chase' and scheme['variant_code'] == 'ppd':
            content = _build_chase_ppd_content(payroll_run, originator_profile, payslips, scheme)
        else:
            lines = [
                f"101 {(originator_profile.debit_routing_number or '000000000')[:9]:<9} {originator_profile.originator_name[:23]:<23}{payroll_run.payment_date:%y%m%d}A094101"
            ]
            for payslip in payslips:
                profile = payslip.payroll_profile
                lines.append(
                    f"6{(profile.default_bank_routing_number if profile else '')[:9]:<9}{(profile.default_bank_account_number if profile else '')[:17]:<17}{str(int((payslip.net_pay or DECIMAL_ZERO) * 100)):>10}{payslip.staff_member.full_name[:22]:<22}{(payslip.bank_payment_reference or '')[:scheme['reference_max_length']]:<15}"
                )
            lines.append(f"9000001{len(payslips):06d}{str(int(sum((payslip.net_pay or DECIMAL_ZERO) for payslip in payslips) * 100)):>12}")
            content = '\n'.join(lines)
        extension = scheme['extension']
    elif file_format == 'sepa':
        content = _build_sepa_content(payroll_run, originator_profile, payslips, scheme)
        extension = scheme['extension']
    elif file_format == 'bacs':
        if scheme['institution_code'] == 'barclays':
            content = _build_barclays_bacs_content(originator_profile, payslips, scheme)
        elif scheme['institution_code'] == 'hsbc':
            content = _build_hsbc_bacs_content(originator_profile, payslips, scheme)
        else:
            lines = [
                'originator_name,originator_account_number,originator_sort_code',
                f'{originator_profile.originator_name},{originator_profile.debit_account_number},{originator_profile.debit_sort_code}',
                'account_name,account_number,sort_code,amount,reference',
            ]
            for payslip in payslips:
                profile = payslip.payroll_profile
                lines.append(','.join([
                    profile.default_bank_account_name if profile else '',
                    profile.default_bank_account_number if profile else '',
                    profile.default_bank_sort_code if profile else '',
                    str(payslip.net_pay),
                    (payslip.bank_payment_reference or '')[:scheme['reference_max_length']],
                ]))
            content = '\n'.join(lines)
        extension = scheme['extension']
    else:
        if scheme['institution_code'] == 'adp' and scheme['variant_code'] == 'workforce_now':
            content = _build_adp_workforce_now_content(originator_profile, payslips, scheme)
        else:
            buffer = StringIO()
            writer = csv.writer(buffer)
            writer.writerow(['originator_name', 'originator_account_number', 'employee_id', 'employee_name', 'account_name', 'account_number', 'routing_number', 'amount', 'reference'])
            for payslip in payslips:
                profile = payslip.payroll_profile
                writer.writerow([
                    originator_profile.originator_name,
                    originator_profile.debit_account_number,
                    payslip.staff_member.employee_id,
                    payslip.staff_member.full_name,
                    profile.default_bank_account_name if profile else '',
                    profile.default_bank_account_number if profile else '',
                    profile.default_bank_routing_number if profile else '',
                    str(payslip.net_pay),
                    (payslip.bank_payment_reference or '')[:scheme['reference_max_length']],
                ])
            content = buffer.getvalue()
        extension = scheme['extension']

    PayrollBankPaymentFile.objects.update_or_create(
        payroll_run=payroll_run,
        defaults={
            'file_format': file_format,
            'file_name': f'payroll_run_{payroll_run.id}_{scheme["institution_code"]}_{scheme["variant_code"].replace(".", "_")}.{extension}',
            'content': content,
            'status': 'generated',
        },
    )


@db_transaction.atomic
def process_payroll_run(payroll_run, acting_user=None):
    if payroll_run.status == 'paid':
        return payroll_run

    ensure_period_is_open(payroll_run.entity, payroll_run.payment_date)

    payroll_run.status = 'processing'
    payroll_run.processed_by = acting_user
    payroll_run.processed_at = timezone.now()
    payroll_run.save(update_fields=['status', 'processed_by', 'processed_at', 'updated_at'])

    payroll_run.payslips.all().delete()
    PayrollStatutoryReport.objects.filter(payroll_run=payroll_run).delete()
    PayrollBankPaymentFile.objects.filter(payroll_run=payroll_run).delete()
    if payroll_run.journal_entry_id:
        payroll_run.journal_entry.delete()
        payroll_run.journal_entry = None
        payroll_run.save(update_fields=['journal_entry', 'updated_at'])

    staff_members = EntityStaff.objects.filter(
        entity=payroll_run.entity,
        status='active',
    ).select_related('payroll_profile').prefetch_related('payroll_component_assignments__component')

    totals = {
        'gross_pay_total': DECIMAL_ZERO,
        'employee_benefits_total': DECIMAL_ZERO,
        'employer_benefits_total': DECIMAL_ZERO,
        'deductions_total': DECIMAL_ZERO,
        'tax_withholding_total': DECIMAL_ZERO,
        'employer_tax_total': DECIMAL_ZERO,
        'net_pay_total': DECIMAL_ZERO,
        'debit_total': DECIMAL_ZERO,
    }
    employee_count = 0

    for staff_member in staff_members:
        profile = getattr(staff_member, 'payroll_profile', None)
        if profile and not profile.is_active:
            profile = None
        preset = _effective_profile_preset(profile, payroll_run.entity)

        base_period_salary = _period_salary(staff_member, profile, profile.pay_frequency if profile else payroll_run.pay_frequency)
        if base_period_salary <= DECIMAL_ZERO:
            continue

        employee_count += 1
        gross_pay = base_period_salary
        taxable_pay = base_period_salary
        employee_benefits_total = DECIMAL_ZERO
        employer_benefits_total = DECIMAL_ZERO
        deductions_total = DECIMAL_ZERO

        assignments = [
            assignment for assignment in staff_member.payroll_component_assignments.all()
            if assignment.is_active
            and (not assignment.effective_start or assignment.effective_start <= payroll_run.period_end)
            and (not assignment.effective_end or assignment.effective_end >= payroll_run.period_start)
        ]

        component_line_items = [
            {
                'category': 'earning',
                'code': 'BASE',
                'description': 'Base salary',
                'amount': base_period_salary,
                'taxable': True,
                'metadata': {},
            }
        ]

        for assignment in assignments:
            amount = _component_amount(assignment, base_period_salary)
            if amount <= DECIMAL_ZERO:
                continue
            component = assignment.component
            if component.component_type == 'earning':
                gross_pay += amount
                if component.taxable:
                    taxable_pay += amount
            elif component.component_type == 'benefit':
                if component.employer_contribution:
                    employer_benefits_total += amount
                else:
                    employee_benefits_total += amount
                    gross_pay += amount
                if component.taxable:
                    taxable_pay += amount
            else:
                deductions_total += amount

            component_line_items.append(
                {
                    'category': component.component_type,
                    'code': component.code,
                    'description': component.name,
                    'amount': amount,
                    'taxable': component.taxable,
                    'metadata': {'employer_contribution': component.employer_contribution},
                }
            )

        combined_employee_tax_rate = _rate(preset['income_tax_rate'] + preset['employee_tax_rate'])
        employer_tax_rate = _rate(preset['employer_tax_rate'])
        tax_withholding = (taxable_pay * combined_employee_tax_rate).quantize(TWOPLACES)
        employer_tax = (taxable_pay * employer_tax_rate).quantize(TWOPLACES)
        net_pay = (gross_pay - deductions_total - tax_withholding).quantize(TWOPLACES)

        leave_accrued_hours, leave_used_hours, leave_balance_hours = _process_leave_for_staff(staff_member, payroll_run)

        payslip = Payslip.objects.create(
            payroll_run=payroll_run,
            staff_member=staff_member,
            payroll_profile=profile,
            gross_pay=gross_pay,
            employee_benefits_total=employee_benefits_total,
            employer_benefits_total=employer_benefits_total,
            deductions_total=deductions_total,
            taxable_pay=taxable_pay,
            tax_withholding=tax_withholding,
            employer_tax=employer_tax,
            net_pay=net_pay,
            leave_accrued_hours=leave_accrued_hours,
            leave_used_hours=leave_used_hours,
            leave_balance_hours=leave_balance_hours,
            bank_payment_reference=(profile.payment_reference if profile and profile.payment_reference else _make_reference('PAY', payroll_run.id, staff_member.employee_id)),
        )

        for line in component_line_items:
            PayslipLineItem.objects.create(
                payslip=payslip,
                category=line['category'],
                code=line['code'],
                description=line['description'],
                amount=line['amount'],
                taxable=line['taxable'],
                metadata=line['metadata'],
            )

        PayslipLineItem.objects.create(
            payslip=payslip,
            category='withholding',
            code='TAX',
            description='Employee tax withholding',
            amount=tax_withholding,
            taxable=False,
            metadata={'rate': str(combined_employee_tax_rate)},
        )
        if employer_tax > DECIMAL_ZERO:
            PayslipLineItem.objects.create(
                payslip=payslip,
                category='employer_tax',
                code='ER-TAX',
                description='Employer payroll tax',
                amount=employer_tax,
                taxable=False,
                metadata={'rate': str(employer_tax_rate)},
            )
        if leave_accrued_hours > DECIMAL_ZERO or leave_used_hours > DECIMAL_ZERO:
            PayslipLineItem.objects.create(
                payslip=payslip,
                category='leave',
                code='LEAVE',
                description='Leave accrual and usage',
                amount=leave_accrued_hours - leave_used_hours,
                taxable=False,
                metadata={
                    'leave_accrued_hours': str(leave_accrued_hours),
                    'leave_used_hours': str(leave_used_hours),
                    'leave_balance_hours': str(leave_balance_hours),
                },
            )

        totals['gross_pay_total'] += gross_pay
        totals['employee_benefits_total'] += employee_benefits_total
        totals['employer_benefits_total'] += employer_benefits_total
        totals['deductions_total'] += deductions_total
        totals['tax_withholding_total'] += tax_withholding
        totals['employer_tax_total'] += employer_tax
        totals['net_pay_total'] += net_pay

    for key in totals:
        totals[key] = totals[key].quantize(TWOPLACES)

    totals['debit_total'] = (
        totals['gross_pay_total'] + totals['employer_benefits_total'] + totals['employer_tax_total']
    ).quantize(TWOPLACES)

    payroll_run.employee_count = employee_count
    payroll_run.gross_pay_total = totals['gross_pay_total']
    payroll_run.employee_benefits_total = totals['employee_benefits_total']
    payroll_run.employer_benefits_total = totals['employer_benefits_total']
    payroll_run.deductions_total = totals['deductions_total']
    payroll_run.tax_withholding_total = totals['tax_withholding_total']
    payroll_run.employer_tax_total = totals['employer_tax_total']
    payroll_run.net_pay_total = totals['net_pay_total']
    payroll_run.statutory_summary = {
        'employee_count': employee_count,
        'gross_pay_total': str(totals['gross_pay_total']),
        'employee_benefits_total': str(totals['employee_benefits_total']),
        'employer_benefits_total': str(totals['employer_benefits_total']),
        'deductions_total': str(totals['deductions_total']),
        'tax_withholding_total': str(totals['tax_withholding_total']),
        'employer_tax_total': str(totals['employer_tax_total']),
        'net_pay_total': str(totals['net_pay_total']),
    }
    payroll_run.status = 'processed'

    journal_entry = _create_journal_entry(payroll_run, acting_user, totals)
    payroll_run.journal_entry = journal_entry
    payroll_run.save(
        update_fields=[
            'employee_count',
            'gross_pay_total',
            'employee_benefits_total',
            'employer_benefits_total',
            'deductions_total',
            'tax_withholding_total',
            'employer_tax_total',
            'net_pay_total',
            'statutory_summary',
            'status',
            'journal_entry',
            'updated_at',
        ]
    )

    _generate_statutory_reports(payroll_run)
    _generate_bank_payment_file(payroll_run)
    return payroll_run


@db_transaction.atomic
def mark_payroll_run_paid(payroll_run):
    payroll_run.status = 'paid'
    payroll_run.save(update_fields=['status', 'updated_at'])
    payroll_run.payslips.update(status='paid', updated_at=timezone.now())
    return payroll_run
