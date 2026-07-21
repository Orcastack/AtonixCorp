"""Security helpers for tax data masking, access control, and risk detection."""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

from django.utils import timezone

from .models import Organization, TaxAuditLog, TaxRiskAlert


FULL_AUDIT_ROLES = {'ORG_OWNER', 'CFO', 'COMPLIANCE_OFFICER'}
PARTIAL_AUDIT_ROLES = {'FINANCE_ANALYST'}
RULE_SET_MANAGEMENT_ROLES = {'ORG_OWNER', 'CFO', 'COMPLIANCE_OFFICER'}


def mask_tax_identifier(value: str | None) -> str:
    if not value:
        return ''
    value = str(value).strip()
    if len(value) <= 4:
        return value
    return f"{'*' * max(len(value) - 4, 0)}{value[-4:]}"


def mask_payroll_amount(value) -> str:
    if value in (None, ''):
        return ''
    return '***MASKED***'


def mask_json_payload(payload):
    if isinstance(payload, dict):
        masked = {}
        for key, value in payload.items():
            lowered = str(key).lower()
            if any(token in lowered for token in ('tax_id', 'taxid', 'registration_number', 'reg_number', 'ssn', 'ein')):
                masked[key] = mask_tax_identifier(value)
            elif any(token in lowered for token in ('payroll', 'salary', 'wage', 'compensation')):
                masked[key] = mask_payroll_amount(value)
            else:
                masked[key] = mask_json_payload(value)
        return masked
    if isinstance(payload, list):
        return [mask_json_payload(item) for item in payload]
    return payload


def can_view_full_tax_audit(user, organization: Organization) -> bool:
    if not user or not getattr(user, 'is_authenticated', False):
        return False
    if organization.owner_id == user.id:
        return True
    member = organization.team_members.select_related('role').filter(user=user, is_active=True).first()
    if member is None:
        return False
    return member.role.code in FULL_AUDIT_ROLES


def should_mask_tax_audit(user, organization: Organization) -> bool:
    return not can_view_full_tax_audit(user, organization)


def can_view_partial_tax_audit(user, organization: Organization) -> bool:
    if can_view_full_tax_audit(user, organization):
        return True
    if not user or not getattr(user, 'is_authenticated', False):
        return False
    member = organization.team_members.select_related('role').filter(user=user, is_active=True).first()
    if member is None:
        return False
    return member.role.code in PARTIAL_AUDIT_ROLES


def can_manage_tax_rule_sets(user, organization: Organization) -> bool:
    if not user or not getattr(user, 'is_authenticated', False):
        return False
    if organization.owner_id == user.id:
        return True
    member = organization.team_members.select_related('role').filter(user=user, is_active=True).first()
    if member is None:
        return False
    return member.role.code in RULE_SET_MANAGEMENT_ROLES


def can_manage_global_tax_rules(user) -> bool:
    if not user or not getattr(user, 'is_authenticated', False):
        return False
    from .models import Organization

    for organization in Organization.objects.filter(owner=user).only('id', 'owner_id'):
        if can_manage_tax_rule_sets(user, organization):
            return True
    for organization in Organization.objects.filter(team_members__user=user, team_members__is_active=True).distinct().only('id', 'owner_id'):
        if can_manage_tax_rule_sets(user, organization):
            return True
    return False


def build_device_metadata(request) -> dict:
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    return {
        'user_agent': user_agent,
        'accept_language': request.META.get('HTTP_ACCEPT_LANGUAGE', ''),
        'x_forwarded_for': request.META.get('HTTP_X_FORWARDED_FOR', ''),
        'x_request_id': request.META.get('HTTP_X_REQUEST_ID', ''),
    }


def detect_tax_risks(entity, action_type: str, old_value=None, new_value=None, source_model: str = '', source_id: str = '', actor=None, persist: bool = True) -> list[dict]:
    alerts: list[dict] = []
    old_value = old_value or {}
    new_value = new_value or {}

    def _as_decimal(value):
        try:
            return Decimal(str(value))
        except Exception:
            return Decimal('0')

    if action_type == 'submit' and new_value.get('submitted_at'):
        submitted_at = datetime.fromisoformat(str(new_value['submitted_at'])) if 'T' in str(new_value['submitted_at']) else None
        if submitted_at and submitted_at.date() < timezone.localdate() - timedelta(days=1):
            alerts.append({
                'alert_type': 'backdated_filing',
                'severity': 'high',
                'title': 'Backdated filing detected',
                'details': {'submitted_at': str(new_value['submitted_at'])},
            })

    if old_value and new_value and old_value != new_value and action_type in {'calculate', 'rule_change'}:
        old_base = _as_decimal(old_value.get('tax_base') or old_value.get('taxable_income'))
        new_base = _as_decimal(new_value.get('tax_base') or new_value.get('taxable_income'))
        if old_base and new_base and abs(new_base - old_base) > (old_base * Decimal('0.50')):
            alerts.append({
                'alert_type': 'manipulated_tax_base',
                'severity': 'critical',
                'title': 'Tax base changed significantly',
                'details': {'old_base': str(old_base), 'new_base': str(new_base)},
            })

    if action_type == 'submit' and source_model == 'TaxFiling':
        duplicate_key = {
            'tax_regime_code': new_value.get('tax_regime_code'),
            'period_start': new_value.get('period_start'),
            'period_end': new_value.get('period_end'),
        }
        if all(duplicate_key.values()):
            alerts.append({
                'alert_type': 'duplicate_filing',
                'severity': 'high',
                'title': 'Potential duplicate filing',
                'details': duplicate_key,
            })

    if action_type == 'rule_change' and old_value != new_value:
        alerts.append({
            'alert_type': 'suspicious_rule_change',
            'severity': 'critical',
            'title': 'Tax rule-set changed',
            'details': {'source_model': source_model, 'source_id': source_id},
        })

    if action_type == 'unauthorized_access':
        alerts.append({
            'alert_type': 'unauthorized_access',
            'severity': 'critical',
            'title': 'Unauthorized tax access attempt',
            'details': {'source_model': source_model, 'source_id': source_id},
        })

    if persist:
        for alert in alerts:
            TaxRiskAlert.objects.create(
                entity=entity,
                alert_type=alert['alert_type'],
                severity=alert['severity'],
                title=alert['title'],
                details=alert['details'],
                source_model=source_model,
                source_id=source_id,
                resolved_at=None,
                resolved_by=None,
            )
    return alerts


def is_tax_audit_action_permitted(user, organization: Organization, action_type: str) -> bool:
    if action_type in {'calculate', 'file', 'submit'}:
        return can_view_full_tax_audit(user, organization)
    return should_mask_tax_audit(user, organization) is False
