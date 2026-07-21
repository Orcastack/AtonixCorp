"""Shared helpers for worldwide tax regime defaults.

The goal is to keep regime selection data-driven so country-specific logic can
be expanded without hard-coding platform behavior in views or models.
"""

from copy import deepcopy

DEFAULT_REGIME_FAMILIES = {
    'corporate_income_tax': {
        'regime_code': 'corporate_income_tax',
        'regime_name': 'Corporate Income Tax',
        'regime_category': 'income_tax',
        'filing_frequency': 'annual',
        'filing_form': 'corporate_return',
        'required_forms': ['corporate_return'],
        'calculation_method': 'profit_based',
        'compliance_rules': {
            'filing_frequency': 'annual',
            'due_day': 30,
            'grace_period_days': 5,
            'penalties': {
                'late_filing': {'type': 'percentage', 'value': 0.10},
                'late_payment': {'type': 'interest', 'rate': 0.01},
            },
        },
        'penalty_rules': {
            'late_filing': 'jurisdiction_defined',
            'late_payment': 'jurisdiction_defined',
        },
        'rule_set': {
            'basis': 'profit',
            'entity_scope': 'corporate',
            'applies_to': ['resident', 'non_resident'],
        },
    },
    'vat': {
        'regime_code': 'vat',
        'regime_name': 'Value Added Tax',
        'regime_category': 'vat',
        'filing_frequency': 'monthly',
        'filing_form': 'vat_return',
        'required_forms': ['vat_return'],
        'calculation_method': 'invoice_offset',
        'compliance_rules': {
            'filing_frequency': 'monthly',
            'due_day': 25,
            'grace_period_days': 5,
            'penalties': {
                'late_filing': {'type': 'percentage', 'value': 0.10},
                'late_payment': {'type': 'interest', 'rate': 0.01},
            },
        },
        'penalty_rules': {
            'late_filing': 'jurisdiction_defined',
            'late_payment': 'jurisdiction_defined',
        },
        'rule_set': {
            'basis': 'supply',
            'collection_mode': 'output_input_offset',
        },
    },
    'sales_tax': {
        'regime_code': 'sales_tax',
        'regime_name': 'Sales Tax',
        'regime_category': 'vat',
        'filing_frequency': 'monthly',
        'filing_form': 'sales_tax_return',
        'required_forms': ['sales_tax_return'],
        'calculation_method': 'point_of_sale',
        'compliance_rules': {
            'filing_frequency': 'monthly',
            'due_day': 20,
            'grace_period_days': 5,
            'penalties': {
                'late_filing': {'type': 'percentage', 'value': 0.10},
                'late_payment': {'type': 'interest', 'rate': 0.01},
            },
        },
        'penalty_rules': {
            'late_filing': 'jurisdiction_defined',
            'late_payment': 'jurisdiction_defined',
        },
        'rule_set': {
            'basis': 'sale_transaction',
            'collection_mode': 'point_of_sale',
        },
    },
    'withholding_tax': {
        'regime_code': 'withholding_tax',
        'regime_name': 'Withholding Tax',
        'regime_category': 'withholding',
        'filing_frequency': 'monthly',
        'filing_form': 'withholding_return',
        'required_forms': ['withholding_return'],
        'calculation_method': 'payment_based',
        'compliance_rules': {
            'filing_frequency': 'monthly',
            'due_day': 15,
            'grace_period_days': 5,
            'penalties': {
                'late_filing': {'type': 'percentage', 'value': 0.10},
                'late_payment': {'type': 'interest', 'rate': 0.01},
            },
        },
        'penalty_rules': {
            'late_filing': 'jurisdiction_defined',
            'late_payment': 'jurisdiction_defined',
        },
        'rule_set': {
            'basis': 'payment',
            'applies_to': ['dividends', 'interest', 'royalties', 'services'],
        },
    },
    'payroll_tax': {
        'regime_code': 'payroll_tax',
        'regime_name': 'Payroll Tax',
        'regime_category': 'payroll',
        'filing_frequency': 'monthly',
        'filing_form': 'payroll_return',
        'required_forms': ['payroll_return'],
        'calculation_method': 'employment_income_based',
        'compliance_rules': {
            'filing_frequency': 'monthly',
            'due_day': 7,
            'grace_period_days': 3,
            'penalties': {
                'late_filing': {'type': 'percentage', 'value': 0.10},
                'late_payment': {'type': 'interest', 'rate': 0.01},
            },
        },
        'penalty_rules': {
            'late_filing': 'jurisdiction_defined',
            'late_payment': 'jurisdiction_defined',
        },
        'rule_set': {
            'basis': 'employment_income',
            'applies_to': ['salary', 'benefits'],
        },
    },
    'property_tax': {
        'regime_code': 'property_tax',
        'regime_name': 'Property Tax',
        'regime_category': 'property',
        'filing_frequency': 'annual',
        'filing_form': 'property_return',
        'required_forms': ['property_return'],
        'calculation_method': 'asset_value_based',
        'compliance_rules': {
            'filing_frequency': 'annual',
            'due_day': 30,
            'grace_period_days': 5,
            'penalties': {
                'late_filing': {'type': 'percentage', 'value': 0.10},
                'late_payment': {'type': 'interest', 'rate': 0.01},
            },
        },
        'penalty_rules': {
            'late_filing': 'jurisdiction_defined',
            'late_payment': 'jurisdiction_defined',
        },
        'rule_set': {
            'basis': 'asset_value',
        },
    },
    'provisional_tax': {
        'regime_code': 'provisional_tax',
        'regime_name': 'Provisional Tax',
        'regime_category': 'income_tax',
        'filing_frequency': 'quarterly',
        'filing_form': 'provisional_return',
        'required_forms': ['provisional_return'],
        'calculation_method': 'estimated_profit_based',
        'compliance_rules': {
            'filing_frequency': 'quarterly',
            'due_day': 25,
            'grace_period_days': 5,
            'penalties': {
                'late_filing': {'type': 'percentage', 'value': 0.10},
                'late_payment': {'type': 'interest', 'rate': 0.01},
            },
        },
        'penalty_rules': {
            'late_filing': 'jurisdiction_defined',
            'late_payment': 'jurisdiction_defined',
        },
        'rule_set': {
            'basis': 'estimated_profit',
            'applies_to': ['corporate', 'individual'],
        },
    },
    'social_security_contribution': {
        'regime_code': 'social_security_contribution',
        'regime_name': 'Social Security Contribution',
        'regime_category': 'payroll',
        'filing_frequency': 'monthly',
        'filing_form': 'social_security_return',
        'required_forms': ['social_security_return'],
        'calculation_method': 'employment_income_based',
        'compliance_rules': {
            'filing_frequency': 'monthly',
            'due_day': 7,
            'grace_period_days': 3,
            'penalties': {
                'late_filing': {'type': 'percentage', 'value': 0.10},
                'late_payment': {'type': 'interest', 'rate': 0.01},
            },
        },
        'penalty_rules': {
            'late_filing': 'jurisdiction_defined',
            'late_payment': 'jurisdiction_defined',
        },
        'rule_set': {
            'basis': 'employment_income',
            'applies_to': ['employer', 'employee'],
        },
    },
    'local_tax': {
        'regime_code': 'local_tax',
        'regime_name': 'Local / State / Provincial Tax',
        'regime_category': 'other',
        'filing_frequency': 'annual',
        'filing_form': 'local_tax_return',
        'required_forms': ['local_tax_return'],
        'calculation_method': 'jurisdiction_defined',
        'compliance_rules': {
            'filing_frequency': 'annual',
            'due_day': 30,
            'grace_period_days': 5,
            'penalties': {
                'late_filing': {'type': 'percentage', 'value': 0.10},
                'late_payment': {'type': 'interest', 'rate': 0.01},
            },
        },
        'penalty_rules': {
            'late_filing': 'jurisdiction_defined',
            'late_payment': 'jurisdiction_defined',
        },
        'rule_set': {
            'basis': 'jurisdiction_specific',
        },
    },
    'digital_services_tax': {
        'regime_code': 'digital_services_tax',
        'regime_name': 'Digital Services Tax',
        'regime_category': 'other',
        'filing_frequency': 'quarterly',
        'filing_form': 'dst_return',
        'required_forms': ['dst_return'],
        'calculation_method': 'gross_revenue_based',
        'compliance_rules': {
            'filing_frequency': 'quarterly',
            'due_day': 25,
            'grace_period_days': 5,
            'penalties': {
                'late_filing': {'type': 'percentage', 'value': 0.10},
                'late_payment': {'type': 'interest', 'rate': 0.01},
            },
        },
        'penalty_rules': {
            'late_filing': 'jurisdiction_defined',
            'late_payment': 'jurisdiction_defined',
        },
        'rule_set': {
            'basis': 'digital_revenue',
        },
    },
    'carbon_tax': {
        'regime_code': 'carbon_tax',
        'regime_name': 'Carbon Tax',
        'regime_category': 'other',
        'filing_frequency': 'annual',
        'filing_form': 'carbon_return',
        'required_forms': ['carbon_return'],
        'calculation_method': 'emissions_based',
        'compliance_rules': {
            'filing_frequency': 'annual',
            'due_day': 30,
            'grace_period_days': 5,
            'penalties': {
                'late_filing': {'type': 'percentage', 'value': 0.10},
                'late_payment': {'type': 'interest', 'rate': 0.01},
            },
        },
        'penalty_rules': {
            'late_filing': 'jurisdiction_defined',
            'late_payment': 'jurisdiction_defined',
        },
        'rule_set': {
            'basis': 'emissions',
        },
    },
    'import_export_duties': {
        'regime_code': 'import_export_duties',
        'regime_name': 'Import / Export Duties',
        'regime_category': 'customs',
        'filing_frequency': 'ad_hoc',
        'filing_form': 'customs_declaration',
        'required_forms': ['customs_declaration'],
        'calculation_method': 'customs_valuation_based',
        'compliance_rules': {
            'filing_frequency': 'event_based',
            'due_day': 0,
            'grace_period_days': 0,
            'penalties': {
                'late_filing': {'type': 'percentage', 'value': 0.10},
                'late_payment': {'type': 'interest', 'rate': 0.01},
            },
        },
        'penalty_rules': {
            'late_filing': 'jurisdiction_defined',
            'late_payment': 'jurisdiction_defined',
        },
        'rule_set': {
            'basis': 'customs_value',
        },
    },
}

REGIME_ALIAS_MAP = {
    'US_FED_CIT': 'corporate_income_tax',
    'US_CIT': 'corporate_income_tax',
    'CT600': 'corporate_income_tax',
    'UK_CT600': 'corporate_income_tax',
    'ZA_CIT': 'corporate_income_tax',
    'IRP6': 'provisional_tax',
    'UK_VAT': 'vat',
    'ZA_VAT201': 'vat',
    'AE_VAT': 'vat',
    'EU_VAT': 'vat',
    'NIC': 'social_security_contribution',
    'PAYE': 'payroll_tax',
    'GST': 'vat',
    'GST_HST': 'vat',
    'PST': 'local_tax',
    'QST': 'local_tax',
    'DST': 'digital_services_tax',
    'CARBON': 'carbon_tax',
    'CUSTOMS': 'import_export_duties',
}

COUNTRY_CODE_MAP = {
    'south africa': 'ZA',
    'za': 'ZA',
    'united states': 'US',
    'us': 'US',
    'usa': 'US',
    'united kingdom': 'GB',
    'uk': 'GB',
    'great britain': 'GB',
    'european union': 'EU',
    'eu': 'EU',
}


COUNTRY_REGIME_MAP = {
    'south africa': ['corporate_income_tax', 'vat', 'withholding_tax', 'payroll_tax', 'property_tax'],
    'za': ['corporate_income_tax', 'vat', 'withholding_tax', 'payroll_tax', 'property_tax'],
    'united states': ['corporate_income_tax', 'sales_tax', 'withholding_tax', 'payroll_tax', 'property_tax'],
    'us': ['corporate_income_tax', 'sales_tax', 'withholding_tax', 'payroll_tax', 'property_tax'],
    'usa': ['corporate_income_tax', 'sales_tax', 'withholding_tax', 'payroll_tax', 'property_tax'],
    'united kingdom': ['corporate_income_tax', 'vat', 'withholding_tax', 'payroll_tax', 'property_tax'],
    'uk': ['corporate_income_tax', 'vat', 'withholding_tax', 'payroll_tax', 'property_tax'],
    'european union': ['corporate_income_tax', 'vat', 'withholding_tax', 'payroll_tax'],
    'eu': ['corporate_income_tax', 'vat', 'withholding_tax', 'payroll_tax'],
}


def normalize_jurisdiction_code(country):
    if not country:
        return 'GLOBAL'
    normalized = str(country).strip()
    if not normalized:
        return 'GLOBAL'
    lowered = normalized.lower()
    if lowered in COUNTRY_CODE_MAP:
        return COUNTRY_CODE_MAP[lowered]
    return normalized.upper().replace(' ', '_')


def normalize_regime_code(regime_code):
    if not regime_code:
        return ''
    normalized = str(regime_code).strip().upper().replace('-', '_').replace(' ', '_')
    return normalized


def resolve_regime_code(regime_code):
    normalized = normalize_regime_code(regime_code)
    if not normalized:
        return ''
    if normalized in REGIME_ALIAS_MAP:
        return REGIME_ALIAS_MAP[normalized]
    lowered = normalized.lower()
    if lowered in DEFAULT_REGIME_FAMILIES:
        return lowered
    if 'vat' in lowered:
        return 'vat'
    if 'gst' in lowered or 'sales_tax' in lowered or 'sales' in lowered:
        return 'sales_tax'
    if 'cit' in lowered or 'ct600' in lowered or 'corporate' in lowered:
        return 'corporate_income_tax'
    if 'paye' in lowered or 'payroll' in lowered:
        return 'payroll_tax'
    if 'withholding' in lowered or 'wh_tax' in lowered:
        return 'withholding_tax'
    if 'prov' in lowered or 'irp6' in lowered:
        return 'provisional_tax'
    if 'nic' in lowered or 'social' in lowered:
        return 'social_security_contribution'
    if 'carbon' in lowered:
        return 'carbon_tax'
    if 'dst' in lowered or 'digital' in lowered:
        return 'digital_services_tax'
    if 'custom' in lowered or 'duty' in lowered:
        return 'import_export_duties'
    if 'property' in lowered or 'franchise' in lowered:
        return 'property_tax'
    return lowered


def get_regime_template(regime_code):
    resolved_code = resolve_regime_code(regime_code)
    template = DEFAULT_REGIME_FAMILIES.get(resolved_code)
    if template is not None:
        built = deepcopy(template)
        built.setdefault('rules_json', built.get('rule_set', {}))
        built.setdefault('forms_json', built.get('required_forms') or ([built['filing_form']] if built.get('filing_form') else []))
        built.setdefault('penalty_rules_json', built.get('penalty_rules', {}))
        built.setdefault('compliance_rules_json', built.get('compliance_rules', {}))
        return built

    if not resolved_code:
        return None

    return {
        'regime_code': resolved_code,
        'regime_name': resolved_code.replace('_', ' ').title(),
        'regime_category': 'other',
        'filing_frequency': 'annual',
        'filing_form': f'{resolved_code}_return',
        'required_forms': [f'{resolved_code}_return'],
        'calculation_method': 'jurisdiction_defined',
        'compliance_rules': {
            'filing_frequency': 'annual',
            'due_day': 30,
            'grace_period_days': 5,
            'penalties': {
                'late_filing': {'type': 'percentage', 'value': 0.10},
                'late_payment': {'type': 'interest', 'rate': 0.01},
            },
        },
        'rules_json': {
            'tax_base': 'jurisdiction_specific',
        },
        'forms_json': [f'{resolved_code}_return'],
        'penalty_rules_json': {
            'late_filing': 'jurisdiction_defined',
            'late_payment': 'jurisdiction_defined',
        },
        'compliance_rules_json': {
            'filing_frequency': 'annual',
            'due_day': 30,
            'grace_period_days': 5,
            'penalties': {
                'late_filing': {'type': 'percentage', 'value': 0.10},
                'late_payment': {'type': 'interest', 'rate': 0.01},
            },
        },
        'penalty_rules': {
            'late_filing': 'jurisdiction_defined',
            'late_payment': 'jurisdiction_defined',
        },
        'rule_set': {
            'basis': 'jurisdiction_specific',
        },
    }


def default_regime_codes_for_country(country):
    if not country:
        return ['corporate_income_tax', 'withholding_tax']

    lowered = str(country).strip().lower()
    if lowered in COUNTRY_REGIME_MAP:
        return COUNTRY_REGIME_MAP[lowered]

    return ['corporate_income_tax', 'withholding_tax', 'payroll_tax']


def normalize_regime_codes(regime_codes):
    if not regime_codes:
        return []

    normalized = []
    for regime_code in regime_codes:
        resolved_code = resolve_regime_code(regime_code)
        if resolved_code and resolved_code not in normalized:
            normalized.append(resolved_code)
    return normalized


def build_regime_payload(regime_code):
    template = get_regime_template(regime_code)
    if template is None:
        return None
    return template


def build_regime_rules(country, regime_codes=None):
    jurisdiction_code = normalize_jurisdiction_code(country)
    resolved_codes = normalize_regime_codes(regime_codes) if regime_codes else default_regime_codes_for_country(country)
    active_regimes = [build_regime_payload(code) for code in resolved_codes]
    active_regimes = [regime for regime in active_regimes if regime is not None]
    required_forms = []
    penalty_rules = {}
    calculation_methods = {}

    for regime in active_regimes:
        for form_code in regime.get('required_forms', []):
            if form_code not in required_forms:
                required_forms.append(form_code)
        if regime.get('regime_code'):
            penalty_rules[regime['regime_code']] = regime.get('penalty_rules', {})
            calculation_methods[regime['regime_code']] = regime.get('calculation_method', 'jurisdiction_defined')

    compliance_rules = {
        'filing_frequency': 'monthly' if any(code in {'vat', 'sales_tax', 'payroll_tax', 'withholding_tax'} for code in resolved_codes) else 'annual',
        'due_day': 25,
        'grace_period_days': 5,
        'penalties': {
            'late_filing': {'type': 'percentage', 'value': 0.10},
            'late_payment': {'type': 'interest', 'rate': 0.01},
        },
    }

    tax_rules = {
        'jurisdiction_code': jurisdiction_code,
        'country': country or jurisdiction_code,
        'regime_codes': resolved_codes,
        'active_regimes': active_regimes,
        'required_forms': required_forms,
        'penalty_rules': penalty_rules,
        'calculation_methods': calculation_methods,
        'compliance_rules': compliance_rules,
        'compliance_rules_json': compliance_rules,
    }

    return {
        'jurisdiction_code': jurisdiction_code,
        'country': country or jurisdiction_code,
        'regime_codes': resolved_codes,
        'active_regimes': active_regimes,
        'tax_rules': tax_rules,
        'required_forms': required_forms,
        'penalty_rules': penalty_rules,
        'calculation_methods': calculation_methods,
        'compliance_rules': compliance_rules,
        'rules_json': tax_rules,
        'forms_json': required_forms,
        'penalty_rules_json': penalty_rules,
        'compliance_rules_json': compliance_rules,
        'filing_preferences': {
            'jurisdiction_code': jurisdiction_code,
            'primary_frequency': 'monthly' if any(code in {'vat', 'sales_tax', 'payroll_tax', 'withholding_tax'} for code in resolved_codes) else 'annual',
            'compliance_mode': 'global_registry',
        },
        'registration_numbers': {},
    }
