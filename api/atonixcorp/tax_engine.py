"""Stateless global tax engine.

The engine resolves a company tax profile plus a tax regime registry payload and
computes a filing-ready result without storing mutable state internally.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from django.db.models import Q
from django.utils import timezone

from .models import Entity, TaxAuditLog, TaxCalculation, TaxFiling, TaxProfile, TaxRegimeRegistry
from .tax_regimes import build_regime_payload, build_regime_rules, resolve_regime_code
from .tax_security import detect_tax_risks


def _to_decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal('0')


def _sum_numeric_values(payload: Any) -> Decimal:
    total = Decimal('0')
    if isinstance(payload, dict):
        for value in payload.values():
            if isinstance(value, (dict, list, tuple)):
                total += _sum_numeric_values(value)
                continue
            total += _to_decimal(value)
    elif isinstance(payload, (list, tuple)):
        for value in payload:
            total += _sum_numeric_values(value)
    return total


def _first_non_zero(*values) -> Decimal:
    for value in values:
        decimal_value = _to_decimal(value)
        if decimal_value != 0:
            return decimal_value
    return Decimal('0')


def _calculate_threshold_adjustment(base_amount: Decimal, threshold_rules: Any) -> Decimal:
    if isinstance(threshold_rules, dict):
        minimum = _to_decimal(threshold_rules.get('minimum'))
        if minimum and base_amount < minimum:
            return Decimal('0')
        return base_amount

    if isinstance(threshold_rules, list):
        for entry in threshold_rules:
            if not isinstance(entry, dict):
                continue
            minimum = _to_decimal(entry.get('minimum'))
            if minimum and base_amount < minimum:
                return Decimal('0')
    return base_amount


def _resolve_registry_record(country_code: str, regime_code: str):
    normalized_code = resolve_regime_code(regime_code)
    if not normalized_code:
        return None

    query = TaxRegimeRegistry.objects.filter(
        Q(jurisdiction_code__iexact=country_code) | Q(country__iexact=country_code)
    ).filter(Q(regime_code__iexact=normalized_code) | Q(tax_type__iexact=normalized_code))

    record = query.filter(is_active=True).order_by('-updated_at', '-created_at').first()
    if record is not None:
        return record

    alias_match = TaxRegimeRegistry.objects.filter(
        Q(regime_code__iexact=normalized_code) | Q(tax_type__iexact=normalized_code),
        is_active=True,
    ).order_by('-updated_at', '-created_at').first()
    if alias_match is not None:
        return alias_match

    return None


def get_tax_profile(entity: Entity, regime_code: str | None = None) -> TaxProfile:
    profiles = TaxProfile.objects.filter(entity=entity).order_by('-updated_at')
    if regime_code:
        normalized = resolve_regime_code(regime_code)
        profile = None
        for candidate in profiles:
            registered_regimes = candidate.registered_regimes if isinstance(candidate.registered_regimes, list) else []
            if normalized in registered_regimes or candidate.jurisdiction_code.lower() == normalized.lower() or candidate.country.lower() == entity.country.lower():
                profile = candidate
                break
        if profile is not None:
            return profile

    profile = profiles.first()
    if profile is not None:
        return profile

    defaults = build_regime_rules(entity.country)
    return TaxProfile.objects.create(
        entity=entity,
        country=entity.country,
        jurisdiction_code=defaults['jurisdiction_code'],
        tax_rules=defaults['tax_rules'],
        registered_regimes=defaults['regime_codes'],
        registration_numbers=defaults['registration_numbers'],
        filing_preferences=defaults['filing_preferences'],
        status='active',
        residency_status='detected',
    )


def get_rule_payload(entity: Entity, regime_code: str, country_code: str | None = None) -> dict:
    normalized_code = resolve_regime_code(regime_code)
    jurisdiction_code = country_code or entity.country
    record = _resolve_registry_record(jurisdiction_code, normalized_code)
    if record is not None:
        rules_json = record.rules_json or record.rule_set or {}
        forms_json = record.forms_json or record.required_forms or ([record.filing_form] if record.filing_form else [])
        penalty_rules_json = record.penalty_rules_json or record.penalty_rules or {}
        compliance_rules_json = record.compliance_rules_json or rules_json.get('compliance_rules') or {}
        return {
            'regime_code': record.regime_code,
            'regime_name': record.regime_name,
            'tax_type': record.tax_type or record.regime_category,
            'country': record.country,
            'jurisdiction_code': record.jurisdiction_code,
            'filing_frequency': record.filing_frequency,
            'calculation_method': record.calculation_method or 'jurisdiction_defined',
            'rules_json': rules_json,
            'forms_json': forms_json,
            'penalty_rules_json': penalty_rules_json,
            'compliance_rules_json': compliance_rules_json,
            'effective_from': record.effective_from,
            'effective_to': record.effective_to,
            'status': 'active' if record.is_active else 'inactive',
        }

    template = build_regime_payload(normalized_code) or {
        'regime_code': normalized_code,
        'regime_name': normalized_code.replace('_', ' ').title() if normalized_code else 'Unknown Tax Regime',
        'tax_type': 'other',
        'country': entity.country,
        'jurisdiction_code': build_regime_rules(entity.country)['jurisdiction_code'],
        'filing_frequency': 'annual',
        'calculation_method': 'jurisdiction_defined',
        'rules_json': {},
        'forms_json': [],
        'penalty_rules_json': {},
        'compliance_rules_json': {},
        'effective_from': None,
        'effective_to': None,
        'status': 'active',
    }
    return template


def calculate_liability(entity: Entity, regime_code: str, period_start=None, period_end=None, payload: dict | None = None) -> dict:
    payload = payload or {}
    profile = get_tax_profile(entity, regime_code)
    rule_payload = get_rule_payload(entity, regime_code, country_code=profile.resolved_jurisdiction_code)
    rules_json = rule_payload.get('rules_json') or {}

    taxable_base_name = rules_json.get('tax_base', 'taxable_income')
    rate = _first_non_zero(
        rules_json.get('rate'),
        rules_json.get('standard_rate'),
        rules_json.get('default_rate'),
        payload.get('tax_rate'),
    )
    if rate > 1:
        rate = rate / Decimal('100')

    tax_base = _to_decimal(payload.get(taxable_base_name))
    if tax_base == 0 and taxable_base_name != 'taxable_income':
        tax_base = _to_decimal(payload.get('taxable_income'))
    if tax_base == 0 and taxable_base_name == 'value_added':
        output_vat = _to_decimal(payload.get('output_vat'))
        input_vat = _to_decimal(payload.get('input_vat'))
        tax_base = output_vat - input_vat

    if tax_base == 0 and taxable_base_name == 'taxable_sales':
        tax_base = _to_decimal(payload.get('taxable_sales'))
    if tax_base == 0 and taxable_base_name == 'employment_income':
        tax_base = _to_decimal(payload.get('employment_income')) or _to_decimal(payload.get('payroll_gross'))
    if tax_base == 0 and taxable_base_name == 'estimated_profit':
        tax_base = _to_decimal(payload.get('estimated_profit'))
    if tax_base == 0 and taxable_base_name == 'asset_value':
        tax_base = _to_decimal(payload.get('asset_value'))
    if tax_base == 0 and taxable_base_name == 'emissions':
        tax_base = _to_decimal(payload.get('emissions'))
    if tax_base == 0 and taxable_base_name == 'digital_revenue':
        tax_base = _to_decimal(payload.get('digital_revenue'))
    if tax_base == 0 and taxable_base_name == 'customs_value':
        tax_base = _to_decimal(payload.get('customs_value'))

    tax_base = _calculate_threshold_adjustment(tax_base, rules_json.get('thresholds') or payload.get('thresholds') or [])

    deductions = payload.get('deductions') or {}
    credits = payload.get('credits') or {}
    exemptions = payload.get('exemptions') or {}
    carryforwards = payload.get('carryforwards') or {}

    deductions_total = _sum_numeric_values(deductions)
    credits_total = _sum_numeric_values(credits)
    exemptions_total = _sum_numeric_values(exemptions)
    carryforward_total = _sum_numeric_values(carryforwards)

    adjusted_base = tax_base - deductions_total - exemptions_total
    if adjusted_base < 0:
        adjusted_base = Decimal('0')

    calculation_method = rule_payload.get('calculation_method') or 'jurisdiction_defined'
    line_items = {
        'taxable_base_name': taxable_base_name,
        'taxable_base': str(tax_base),
        'deductions_total': str(deductions_total),
        'credits_total': str(credits_total),
        'exemptions_total': str(exemptions_total),
        'carryforward_total': str(carryforward_total),
        'calculation_method': calculation_method,
        'rule_family': rule_payload.get('regime_code'),
        'jurisdiction_code': rule_payload.get('jurisdiction_code') or profile.resolved_jurisdiction_code,
        'regime_code': rule_payload.get('regime_code'),
        'regime_name': rule_payload.get('regime_name'),
        'required_forms': rule_payload.get('forms_json') or [],
    }

    if taxable_base_name == 'value_added':
        liability = tax_base
        if liability < 0:
            liability = Decimal('0')
    elif calculation_method == 'invoice_offset':
        liability = adjusted_base * rate - credits_total
    elif calculation_method == 'point_of_sale':
        liability = adjusted_base * rate - credits_total
    elif calculation_method == 'payment_based':
        liability = adjusted_base * rate - credits_total
    elif calculation_method == 'employment_income_based':
        liability = adjusted_base * rate - credits_total
    elif calculation_method == 'asset_value_based':
        liability = adjusted_base * rate - credits_total
    elif calculation_method == 'emissions_based':
        liability = adjusted_base * rate - credits_total
    elif calculation_method == 'gross_revenue_based':
        liability = adjusted_base * rate - credits_total
    elif calculation_method == 'customs_valuation_based':
        liability = adjusted_base * rate - credits_total
    elif calculation_method == 'estimated_profit_based':
        liability = adjusted_base * rate - credits_total
    else:
        liability = adjusted_base * rate - credits_total

    liability = liability - carryforward_total
    if liability < 0:
        liability = Decimal('0')

    liability = liability.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    effective_rate = Decimal('0')
    if tax_base > 0:
        effective_rate = (liability / tax_base).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)

    filing_output = {
        'jurisdiction_code': rule_payload.get('jurisdiction_code') or profile.resolved_jurisdiction_code,
        'country_code': (rule_payload.get('country') or entity.country),
        'regime_code': rule_payload.get('regime_code'),
        'regime_name': rule_payload.get('regime_name'),
        'form_type': (rule_payload.get('forms_json') or [f"{rule_payload.get('regime_code', 'tax')}_return"])[0],
        'forms_json': rule_payload.get('forms_json') or [],
        'period_start': period_start.isoformat() if period_start else None,
        'period_end': period_end.isoformat() if period_end else None,
        'liability_amount': str(liability),
        'summary': {
            'tax_base': str(tax_base),
            'effective_rate': str(effective_rate),
            'calculation_method': calculation_method,
        },
        'supporting_schedules': payload.get('supporting_schedules') or [],
    }

    calculation_json = {
        'profile': {
            'country': profile.country,
            'jurisdiction_code': profile.resolved_jurisdiction_code,
            'registered_regimes': profile.active_regime_codes,
            'registration_numbers': profile.registration_numbers,
            'filing_preferences': profile.filing_preferences,
        },
        'rules': {
            'regime_code': rule_payload.get('regime_code'),
            'regime_name': rule_payload.get('regime_name'),
            'tax_type': rule_payload.get('tax_type'),
            'filing_frequency': rule_payload.get('filing_frequency'),
            'calculation_method': calculation_method,
            'rules_json': rules_json,
            'forms_json': rule_payload.get('forms_json') or [],
            'penalty_rules_json': rule_payload.get('penalty_rules_json') or {},
            'effective_from': rule_payload.get('effective_from').isoformat() if rule_payload.get('effective_from') else None,
            'effective_to': rule_payload.get('effective_to').isoformat() if rule_payload.get('effective_to') else None,
            'status': rule_payload.get('status'),
        },
        'inputs': payload,
        'line_items': line_items,
        'filing_output': filing_output,
        'computed_at': timezone.now().isoformat(),
    }

    return {
        'entity': entity,
        'profile': profile,
        'rule_payload': rule_payload,
        'calculation_json': calculation_json,
        'liability_amount': liability,
        'effective_rate': effective_rate,
        'filing_output': filing_output,
    }


def persist_tax_calculation(entity: Entity, regime_code: str, period_start, period_end, payload: dict | None = None, tax_year: int | None = None, calculation_type: str | None = None, jurisdiction: str | None = None, status: str = 'draft') -> TaxCalculation:
    result = calculate_liability(entity=entity, regime_code=regime_code, period_start=period_start, period_end=period_end, payload=payload)
    rule_payload = result['rule_payload']
    tax_year = tax_year or (period_end.year if period_end else timezone.now().year)
    calculation_type = calculation_type or rule_payload.get('tax_type') or 'corporate'
    jurisdiction = jurisdiction or rule_payload.get('country') or entity.country

    defaults = {
        'regime_code': rule_payload.get('regime_code') or resolve_regime_code(regime_code),
        'regime_name': rule_payload.get('regime_name') or '',
        'period_start': period_start,
        'period_end': period_end,
        'calculation_json': result['calculation_json'],
        'liability_amount': result['liability_amount'],
        'status': status,
        'taxable_income': _to_decimal((payload or {}).get('taxable_income')),
        'tax_rate': _to_decimal((payload or {}).get('tax_rate')) if _to_decimal((payload or {}).get('tax_rate')) <= 1 else _to_decimal((payload or {}).get('tax_rate')) / Decimal('100'),
        'deductions': (payload or {}).get('deductions') or {},
        'credits': (payload or {}).get('credits') or {},
        'calculated_tax': result['liability_amount'],
        'effective_rate': result['effective_rate'],
        'breakdown': result['calculation_json'].get('line_items') or {},
    }

    calculation, _created = TaxCalculation.objects.update_or_create(
        entity=entity,
        tax_year=tax_year,
        calculation_type=calculation_type,
        jurisdiction=jurisdiction,
        defaults=defaults,
    )
    return calculation


def build_tax_filing(entity: Entity, calculation: TaxCalculation, form_type: str | None = None, reference_number: str | None = None, submission_status: str = 'draft') -> TaxFiling:
    filing_output = (calculation.calculation_json or {}).get('filing_output', {})
    period_start = calculation.period_start or timezone.now().date()
    period_end = calculation.period_end or timezone.now().date()
    filing, created = TaxFiling.objects.update_or_create(
        entity=entity,
        tax_regime_code=calculation.regime_code,
        period_start=period_start,
        period_end=period_end,
        defaults={
            'form_type': form_type or filing_output.get('form_type') or calculation.regime_code,
            'form_json': filing_output,
            'calculation': calculation,
            'submission_status': submission_status,
            'reference_number': reference_number or '',
        },
    )
    if not created:
        detect_tax_risks(
            entity=entity,
            action_type='submit',
            old_value={'tax_regime_code': filing.tax_regime_code, 'period_start': str(filing.period_start), 'period_end': str(filing.period_end)},
            new_value={'tax_regime_code': filing.tax_regime_code, 'period_start': str(filing.period_start), 'period_end': str(filing.period_end)},
            source_model='TaxFiling',
            source_id=str(filing.id),
            persist=True,
        )
    return filing


def log_tax_audit(entity: Entity, action_type: str, user=None, old_value_json=None, new_value_json=None, reason: str = '', ip_address: str | None = None, device_metadata: dict | None = None, country: str | None = None) -> TaxAuditLog:
    audit_log = TaxAuditLog.objects.create(
        entity=entity,
        user=user,
        action_type=action_type,
        old_value_json=old_value_json or {},
        new_value_json=new_value_json or {},
        reason=reason,
        ip_address=ip_address,
        device_metadata=device_metadata or {},
        country=country or entity.country,
    )
    detect_tax_risks(
        entity=entity,
        action_type=action_type,
        old_value=old_value_json or {},
        new_value=new_value_json or {},
        source_model='TaxAuditLog',
        source_id=str(audit_log.id),
        actor=user,
        persist=True,
    )
    return audit_log
