"""Stateless compliance helpers for global tax workflows."""

from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime, timedelta

from django.db import transaction
from django.utils import timezone

from .models import ComplianceDeadline, Entity, TaxProfile, TaxRegimeRegistry
from .tax_engine import get_rule_payload
from .tax_regimes import build_regime_payload, resolve_regime_code


FREQUENCY_MONTHS = {
    'monthly': 1,
    'bi_monthly': 2,
    'quarterly': 3,
    'semi_annual': 6,
    'annual': 12,
}

ALERT_WINDOWS = [30, 14, 7, 3, 1, 0]


def _coerce_date(value) -> date | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        try:
            return datetime.fromisoformat(str(value)).date()
        except ValueError:
            return None


def _month_start(target: date) -> date:
    return target.replace(day=1)


def _month_end(target: date) -> date:
    return target.replace(day=monthrange(target.year, target.month)[1])


def _add_months(target: date, months: int) -> date:
    month_index = target.month - 1 + months
    year = target.year + month_index // 12
    month = month_index % 12 + 1
    day = min(target.day, monthrange(year, month)[1])
    return date(year, month, day)


def _shift_to_business_day(target: date) -> date:
    shifted = target
    while shifted.weekday() >= 5:
        shifted += timedelta(days=1)
    return shifted


def _rule_frequency(rule_payload: dict, registry_record: TaxRegimeRegistry | None = None) -> str:
    compliance_rules = (rule_payload.get('compliance_rules_json') or {}) if isinstance(rule_payload, dict) else {}
    if not compliance_rules and isinstance(rule_payload, dict):
        compliance_rules = (rule_payload.get('rules_json') or {}).get('compliance_rules') or {}
    frequency = compliance_rules.get('filing_frequency') or rule_payload.get('filing_frequency') if isinstance(rule_payload, dict) else None
    if frequency:
        return str(frequency)
    if registry_record is not None:
        return registry_record.filing_frequency
    return 'annual'


def _compliance_rules(rule_payload: dict, registry_record: TaxRegimeRegistry | None = None) -> dict:
    compliance_rules = {}
    if isinstance(rule_payload, dict):
        compliance_rules = rule_payload.get('compliance_rules_json') or (rule_payload.get('rules_json') or {}).get('compliance_rules') or rule_payload.get('compliance_rules') or {}
    if not compliance_rules and registry_record is not None:
        compliance_rules = registry_record.compliance_rules_json or {}
    if not compliance_rules:
        compliance_rules = {
            'filing_frequency': registry_record.filing_frequency if registry_record else 'annual',
            'due_day': 30,
            'grace_period_days': 5,
            'penalties': {
                'late_filing': {'type': 'percentage', 'value': 0.10},
                'late_payment': {'type': 'interest', 'rate': 0.01},
            },
        }
    return compliance_rules


def _cycle_periods(anchor: date, frequency: str, horizon_months: int) -> list[tuple[date, date]]:
    if frequency == 'event_based':
        return [(anchor, anchor)]
    months = FREQUENCY_MONTHS.get(frequency, 12)
    periods = []
    start = _month_start(anchor)
    horizon_end = _add_months(start, max(horizon_months, months))
    while start < horizon_end:
        end = _month_end(_add_months(start, months - 1))
        periods.append((start, end))
        start = _add_months(start, months)
    return periods


def _due_date_for_period(period_end: date, compliance_rules: dict) -> date:
    if compliance_rules.get('filing_frequency') == 'event_based':
        due_date = _coerce_date(compliance_rules.get('due_date')) or period_end
        return _shift_to_business_day(due_date)

    due_day = int(compliance_rules.get('due_day') or 0)
    grace_period_days = int(compliance_rules.get('grace_period_days') or 0)
    base = _add_months(period_end, 1)
    due_day = due_day or min(30, monthrange(base.year, base.month)[1])
    due_date = date(base.year, base.month, min(due_day, monthrange(base.year, base.month)[1]))
    due_date = _shift_to_business_day(due_date)
    if grace_period_days:
        due_date = due_date + timedelta(days=0)
    return due_date


def _resolve_deadline_status(due_date: date, completed_at: date | None = None) -> str:
    if completed_at is not None:
        return 'completed'
    today = timezone.localdate()
    if due_date < today:
        return 'overdue'
    if due_date <= today + timedelta(days=7):
        return 'due_soon'
    return 'upcoming'


def get_entity_tax_profiles(entity: Entity) -> list[TaxProfile]:
    profiles = list(TaxProfile.objects.filter(entity=entity, status='active').order_by('country'))
    if profiles:
        return profiles
    fallback_country = entity.country or ''
    if fallback_country:
        fallback_profile = TaxProfile.objects.filter(entity=entity, country=fallback_country).first()
        return [fallback_profile] if fallback_profile else []
    return []


def build_compliance_calendar(entity: Entity, horizon_months: int = 12, persist: bool = True) -> list[dict]:
    calendar_entries: list[dict] = []
    profiles = get_entity_tax_profiles(entity)
    today = timezone.localdate()

    for profile in profiles:
        active_regimes = profile.active_regime_codes or []
        if not active_regimes:
            active_regimes = build_regime_payload(profile.country).get('regime_codes', [])
        for regime_code in active_regimes:
            resolved_code = resolve_regime_code(regime_code)
            rule_payload = get_rule_payload(entity, resolved_code, country_code=profile.resolved_jurisdiction_code)
            registry_record = TaxRegimeRegistry.objects.filter(
                jurisdiction_code=profile.resolved_jurisdiction_code,
                regime_code=resolved_code,
            ).first()
            compliance_rules = _compliance_rules(rule_payload, registry_record)
            frequency = _rule_frequency(rule_payload, registry_record)
            periods = _cycle_periods(today, frequency, horizon_months)

            for period_start, period_end in periods:
                due_date = _due_date_for_period(period_end, compliance_rules)
                grace_period_days = int(compliance_rules.get('grace_period_days') or 0)
                grace_due_date = due_date + timedelta(days=grace_period_days)
                title = f"{rule_payload.get('regime_name') or resolved_code.replace('_', ' ').title()} - {period_end.isoformat()}"
                existing_deadline = ComplianceDeadline.objects.filter(
                    entity=entity,
                    title=title,
                    deadline_type='tax_filing',
                ).first()
                status = _resolve_deadline_status(due_date, existing_deadline.completed_at if existing_deadline else None)

                if persist:
                    defaults = {
                        'organization': entity.organization,
                        'deadline_type': 'tax_filing',
                        'deadline_date': due_date,
                        'status': status,
                        'description': f"{rule_payload.get('filing_form') or 'Tax return'} due for {profile.country}",
                    }
                    ComplianceDeadline.objects.update_or_create(
                        entity=entity,
                        title=title,
                        deadline_type='tax_filing',
                        defaults=defaults,
                    )

                calendar_entries.append({
                    'entity_id': entity.id,
                    'entity_name': entity.name,
                    'country': profile.country,
                    'jurisdiction_code': profile.resolved_jurisdiction_code,
                    'regime_code': resolved_code,
                    'regime_name': rule_payload.get('regime_name'),
                    'tax_type': rule_payload.get('tax_type'),
                    'period_start': period_start.isoformat(),
                    'period_end': period_end.isoformat(),
                    'due_date': due_date.isoformat(),
                    'grace_due_date': grace_due_date.isoformat(),
                    'status': status,
                    'filing_frequency': frequency,
                    'filing_form': rule_payload.get('forms_json', [rule_payload.get('filing_form')])[0] if (rule_payload.get('forms_json') or rule_payload.get('filing_form')) else None,
                    'required_forms': rule_payload.get('forms_json') or [],
                    'compliance_rules': compliance_rules,
                })

    calendar_entries.sort(key=lambda entry: entry['due_date'])
    return calendar_entries


def build_compliance_alerts(entity: Entity, window_days: int = 30) -> list[dict]:
    alerts: list[dict] = []
    today = timezone.localdate()
    calendar_entries = build_compliance_calendar(entity, horizon_months=max(12, window_days // 30 + 1), persist=False)

    for entry in calendar_entries:
        due_date = date.fromisoformat(entry['due_date'])
        days_remaining = (due_date - today).days
        alert_state = None
        if days_remaining < 0:
            alert_state = 'overdue'
        elif days_remaining <= 7:
            alert_state = 'critical'
        elif days_remaining <= 14:
            alert_state = 'warning'
        elif days_remaining <= window_days:
            alert_state = 'upcoming'

        if alert_state is None:
            continue

        alerts.append({
            **entry,
            'days_remaining': days_remaining,
            'alert_state': alert_state,
        })

    alerts.sort(key=lambda entry: (entry['days_remaining'], entry['due_date']))
    return alerts


def persist_compliance_calendar(entity: Entity, horizon_months: int = 12) -> list[dict]:
    with transaction.atomic():
        return build_compliance_calendar(entity, horizon_months=horizon_months, persist=True)
