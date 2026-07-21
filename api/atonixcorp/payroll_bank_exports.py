import re


BANK_EXPORT_SCHEMES = {
    'csv': {
        'generic': {
            'standard': {
                'label': 'Generic CSV',
                'required_profile_fields': ['default_bank_account_number'],
                'required_originator_fields': ['originator_name'],
                'originator_field_rules': {
                    'originator_name': {'max_length': 70},
                },
                'reference_max_length': 30,
                'reference_pattern': r"^[A-Za-z0-9 ./_-]+$",
                'extension': 'csv',
            },
        },
        'adp': {
            'workforce_now': {
                'label': 'ADP Workforce Now CSV',
                'required_profile_fields': ['default_bank_account_name', 'default_bank_account_number'],
                'required_originator_fields': ['originator_name', 'originator_identifier'],
                'originator_field_rules': {
                    'originator_name': {'max_length': 40},
                    'originator_identifier': {'max_length': 20, 'pattern': r'^[A-Za-z0-9_-]+$'},
                },
                'profile_field_rules': {
                    'default_bank_account_name': {'max_length': 35},
                    'default_bank_account_number': {'max_length': 17, 'pattern': r'^[A-Za-z0-9]+$'},
                },
                'reference_max_length': 20,
                'reference_pattern': r'^[A-Za-z0-9_-]+$',
                'extension': 'csv',
            },
        },
    },
    'aba': {
        'generic': {
            'standard': {
                'label': 'Generic ABA',
                'required_profile_fields': ['default_bank_account_number', 'default_bank_routing_number'],
                'required_originator_fields': ['originator_name', 'debit_account_number', 'debit_routing_number'],
                'originator_field_rules': {
                    'originator_name': {'max_length': 23},
                    'debit_account_number': {'max_length': 17, 'pattern': r'^[A-Za-z0-9]+$'},
                    'debit_routing_number': {'pattern': r'^\d{9}$'},
                },
                'profile_field_rules': {
                    'default_bank_account_number': {'max_length': 17, 'pattern': r'^[A-Za-z0-9]+$'},
                    'default_bank_routing_number': {'pattern': r'^\d{9}$'},
                },
                'reference_max_length': 15,
                'reference_pattern': r'^[A-Za-z0-9 -]+$',
                'extension': 'txt',
            },
        },
        'wells_fargo': {
            'ppd': {
                'label': 'Wells Fargo PPD',
                'required_profile_fields': ['default_bank_account_number', 'default_bank_routing_number'],
                'required_originator_fields': ['originator_name', 'originator_identifier', 'debit_account_number', 'debit_routing_number', 'company_entry_description'],
                'originator_field_rules': {
                    'originator_name': {'max_length': 23},
                    'originator_identifier': {'max_length': 10, 'pattern': r'^[A-Za-z0-9-]+$'},
                    'debit_account_number': {'max_length': 17, 'pattern': r'^[A-Za-z0-9]+$'},
                    'debit_routing_number': {'pattern': r'^\d{9}$'},
                    'company_entry_description': {'max_length': 10, 'pattern': r'^[A-Za-z0-9 ]+$'},
                    'company_discretionary_data': {'max_length': 20, 'pattern': r'^[A-Za-z0-9 ]*$'},
                },
                'profile_field_rules': {
                    'default_bank_account_number': {'max_length': 17, 'pattern': r'^[A-Za-z0-9]+$'},
                    'default_bank_routing_number': {'pattern': r'^\d{9}$'},
                },
                'reference_max_length': 10,
                'reference_pattern': r'^[A-Za-z0-9 -]+$',
                'extension': 'txt',
            },
        },
        'chase': {
            'ppd': {
                'label': 'Chase PPD',
                'required_profile_fields': ['default_bank_account_number', 'default_bank_routing_number'],
                'required_originator_fields': ['originator_name', 'originator_identifier', 'debit_account_number', 'debit_routing_number', 'company_entry_description'],
                'originator_field_rules': {
                    'originator_name': {'max_length': 23},
                    'originator_identifier': {'max_length': 12, 'pattern': r'^[A-Za-z0-9-]+$'},
                    'debit_account_number': {'max_length': 17, 'pattern': r'^[A-Za-z0-9]+$'},
                    'debit_routing_number': {'pattern': r'^\d{9}$'},
                    'company_entry_description': {'max_length': 10, 'pattern': r'^[A-Za-z0-9 ]+$'},
                },
                'profile_field_rules': {
                    'default_bank_account_number': {'max_length': 17, 'pattern': r'^[A-Za-z0-9]+$'},
                    'default_bank_routing_number': {'pattern': r'^\d{9}$'},
                },
                'reference_max_length': 12,
                'reference_pattern': r'^[A-Za-z0-9 -]+$',
                'extension': 'txt',
            },
        },
    },
    'sepa': {
        'generic': {
            'pain.001.001.03': {
                'label': 'Generic SEPA pain.001.001.03',
                'required_profile_fields': ['default_bank_iban', 'default_bank_swift_code'],
                'required_originator_fields': ['originator_name', 'debit_iban', 'debit_swift_code', 'initiating_party_name'],
                'originator_field_rules': {
                    'originator_name': {'max_length': 70},
                    'initiating_party_name': {'max_length': 70},
                    'debit_iban': {'pattern': r'^[A-Z]{2}[0-9A-Z]{13,32}$'},
                    'debit_swift_code': {'pattern': r'^[A-Z0-9]{8}([A-Z0-9]{3})?$'},
                },
                'profile_field_rules': {
                    'default_bank_iban': {'pattern': r'^[A-Z]{2}[0-9A-Z]{13,32}$'},
                    'default_bank_swift_code': {'pattern': r'^[A-Z0-9]{8}([A-Z0-9]{3})?$'},
                },
                'reference_max_length': 35,
                'reference_pattern': r"^[A-Za-z0-9+?/:().,' -]+$",
                'extension': 'xml',
                'xml_namespace': 'urn:iso:std:iso:20022:tech:xsd:pain.001.001.03',
            },
        },
        'deutsche_bank': {
            'pain.001.001.03': {
                'label': 'Deutsche Bank pain.001.001.03',
                'required_profile_fields': ['default_bank_iban', 'default_bank_swift_code'],
                'required_originator_fields': ['originator_name', 'initiating_party_name', 'initiating_party_identifier', 'debit_iban', 'debit_swift_code'],
                'originator_field_rules': {
                    'originator_name': {'max_length': 70},
                    'initiating_party_name': {'max_length': 70},
                    'initiating_party_identifier': {'max_length': 35, 'pattern': r'^[A-Za-z0-9./_-]+$'},
                    'debit_iban': {'pattern': r'^[A-Z]{2}[0-9A-Z]{13,32}$'},
                    'debit_swift_code': {'pattern': r'^[A-Z0-9]{8}([A-Z0-9]{3})?$'},
                },
                'profile_field_rules': {
                    'default_bank_iban': {'pattern': r'^[A-Z]{2}[0-9A-Z]{13,32}$'},
                    'default_bank_swift_code': {'pattern': r'^[A-Z0-9]{8}([A-Z0-9]{3})?$'},
                },
                'reference_max_length': 35,
                'reference_pattern': r"^[A-Za-z0-9+?/:().,' -]+$",
                'extension': 'xml',
                'xml_namespace': 'urn:iso:std:iso:20022:tech:xsd:pain.001.001.03',
            },
        },
        'santander': {
            'pain.001.003.03': {
                'label': 'Santander pain.001.003.03',
                'required_profile_fields': ['default_bank_iban', 'default_bank_swift_code'],
                'required_originator_fields': ['originator_name', 'initiating_party_name', 'initiating_party_identifier', 'debit_iban', 'debit_swift_code'],
                'originator_field_rules': {
                    'originator_name': {'max_length': 70},
                    'initiating_party_name': {'max_length': 70},
                    'initiating_party_identifier': {'max_length': 35, 'pattern': r'^[A-Za-z0-9./_-]+$'},
                    'debit_iban': {'pattern': r'^[A-Z]{2}[0-9A-Z]{13,32}$'},
                    'debit_swift_code': {'pattern': r'^[A-Z0-9]{8}([A-Z0-9]{3})?$'},
                },
                'profile_field_rules': {
                    'default_bank_iban': {'pattern': r'^[A-Z]{2}[0-9A-Z]{13,32}$'},
                    'default_bank_swift_code': {'pattern': r'^[A-Z0-9]{8}([A-Z0-9]{3})?$'},
                },
                'reference_max_length': 35,
                'reference_pattern': r"^[A-Za-z0-9+?/:().,' -]+$",
                'extension': 'xml',
                'xml_namespace': 'urn:iso:std:iso:20022:tech:xsd:pain.001.003.03',
            },
        },
    },
    'bacs': {
        'generic': {
            'standard': {
                'label': 'Generic BACS',
                'required_profile_fields': ['default_bank_account_number', 'default_bank_sort_code'],
                'required_originator_fields': ['originator_name', 'debit_account_number', 'debit_sort_code'],
                'originator_field_rules': {
                    'originator_name': {'max_length': 18},
                    'debit_account_number': {'pattern': r'^\d{8}$'},
                    'debit_sort_code': {'pattern': r'^(\d{2}-?\d{2}-?\d{2})$'},
                },
                'profile_field_rules': {
                    'default_bank_account_number': {'pattern': r'^\d{8}$'},
                    'default_bank_sort_code': {'pattern': r'^(\d{2}-?\d{2}-?\d{2})$'},
                },
                'reference_max_length': 18,
                'reference_pattern': r'^[A-Za-z0-9 ]+$',
                'extension': 'txt',
            },
        },
        'barclays': {
            'standard': {
                'label': 'Barclays BACS',
                'required_profile_fields': ['default_bank_account_number', 'default_bank_sort_code'],
                'required_originator_fields': ['originator_name', 'originator_identifier', 'debit_account_name', 'debit_account_number', 'debit_sort_code'],
                'originator_field_rules': {
                    'originator_name': {'max_length': 18},
                    'originator_identifier': {'max_length': 6, 'pattern': r'^[A-Za-z0-9]+$'},
                    'debit_account_name': {'max_length': 18},
                    'debit_account_number': {'pattern': r'^\d{8}$'},
                    'debit_sort_code': {'pattern': r'^(\d{2}-?\d{2}-?\d{2})$'},
                },
                'profile_field_rules': {
                    'default_bank_account_number': {'pattern': r'^\d{8}$'},
                    'default_bank_sort_code': {'pattern': r'^(\d{2}-?\d{2}-?\d{2})$'},
                },
                'reference_max_length': 18,
                'reference_pattern': r'^[A-Za-z0-9 ]+$',
                'extension': 'txt',
            },
        },
        'hsbc': {
            'standard': {
                'label': 'HSBC BACS',
                'required_profile_fields': ['default_bank_account_number', 'default_bank_sort_code'],
                'required_originator_fields': ['originator_name', 'originator_identifier', 'debit_account_name', 'debit_account_number', 'debit_sort_code'],
                'originator_field_rules': {
                    'originator_name': {'max_length': 18},
                    'originator_identifier': {'max_length': 10, 'pattern': r'^[A-Za-z0-9]+$'},
                    'debit_account_name': {'max_length': 18},
                    'debit_account_number': {'pattern': r'^\d{8}$'},
                    'debit_sort_code': {'pattern': r'^(\d{2}-?\d{2}-?\d{2})$'},
                },
                'profile_field_rules': {
                    'default_bank_account_number': {'pattern': r'^\d{8}$'},
                    'default_bank_sort_code': {'pattern': r'^(\d{2}-?\d{2}-?\d{2})$'},
                },
                'reference_max_length': 18,
                'reference_pattern': r'^[A-Za-z0-9 ]+$',
                'extension': 'txt',
            },
        },
    },
}


FIELD_LABELS = {
    'originator_name': 'originator name',
    'originator_identifier': 'originator identifier',
    'debit_account_number': 'debit account number',
    'debit_routing_number': 'debit routing number',
    'debit_iban': 'debit IBAN',
    'debit_swift_code': 'debit SWIFT/BIC',
    'debit_sort_code': 'debit sort code',
    'company_entry_description': 'company entry description',
    'company_discretionary_data': 'company discretionary data',
    'initiating_party_name': 'initiating party name',
    'initiating_party_identifier': 'initiating party identifier',
    'default_bank_account_name': 'account name',
    'default_bank_account_number': 'account number',
    'default_bank_routing_number': 'routing number',
    'default_bank_iban': 'IBAN',
    'default_bank_swift_code': 'SWIFT/BIC',
    'default_bank_sort_code': 'sort code',
}


FIELD_PATTERNS = {
    'debit_routing_number': re.compile(r'^\d{9}$'),
    'debit_sort_code': re.compile(r'^(\d{2}-?\d{2}-?\d{2})$'),
    'debit_swift_code': re.compile(r'^[A-Z0-9]{8}([A-Z0-9]{3})?$'),
    'debit_iban': re.compile(r'^[A-Z]{2}[0-9A-Z]{13,32}$'),
    'default_bank_routing_number': re.compile(r'^\d{9}$'),
    'default_bank_sort_code': re.compile(r'^(\d{2}-?\d{2}-?\d{2})$'),
    'default_bank_swift_code': re.compile(r'^[A-Z0-9]{8}([A-Z0-9]{3})?$'),
    'default_bank_iban': re.compile(r'^[A-Z]{2}[0-9A-Z]{13,32}$'),
}


def list_bank_export_options(country_code=None):
    results = []
    for file_format, institutions in BANK_EXPORT_SCHEMES.items():
        result = {
            'file_format': file_format,
            'institutions': [],
        }
        for institution_code, variants in institutions.items():
            result['institutions'].append({
                'institution_code': institution_code,
                'variants': [
                    {'variant_code': variant_code, **variant_config}
                    for variant_code, variant_config in variants.items()
                ],
            })
        results.append(result)
    return results


def resolve_bank_export_scheme(file_format, institution_code='', variant_code=''):
    formats = BANK_EXPORT_SCHEMES.get(file_format) or BANK_EXPORT_SCHEMES['csv']
    institution = institution_code if institution_code in formats else 'generic'
    variants = formats[institution]
    variant = variant_code if variant_code in variants else next(iter(variants.keys()))
    resolved = dict(variants[variant])
    resolved.update({
        'file_format': file_format if file_format in BANK_EXPORT_SCHEMES else 'csv',
        'institution_code': institution,
        'variant_code': variant,
    })
    return resolved


def validate_bank_export_profiles(payslips, originator_profile, scheme):
    errors = []
    required_fields = scheme.get('required_profile_fields', [])
    required_originator_fields = scheme.get('required_originator_fields', [])
    profile_field_rules = scheme.get('profile_field_rules', {})
    originator_field_rules = scheme.get('originator_field_rules', {})
    reference_max_length = scheme.get('reference_max_length', 35)
    reference_pattern = scheme.get('reference_pattern')

    def _validate_value(value, field_name, rules):
        issues = []
        if value in (None, ''):
            return issues
        normalized = str(value).upper() if 'iban' in field_name or 'swift' in field_name else str(value)
        pattern = rules.get('pattern')
        if pattern and not re.match(pattern, normalized):
            issues.append(FIELD_LABELS.get(field_name, field_name))
        max_length = rules.get('max_length')
        if max_length and len(str(value)) > max_length:
            issues.append(f"{FIELD_LABELS.get(field_name, field_name)} longer than {max_length} characters")
        return issues

    originator_missing = []
    originator_invalid = []
    for field_name in required_originator_fields:
        value = getattr(originator_profile, field_name, '') if originator_profile else ''
        if not value:
            originator_missing.append(FIELD_LABELS.get(field_name, field_name))
            continue
        pattern = FIELD_PATTERNS.get(field_name)
        if pattern and not pattern.match(str(value).upper()):
            originator_invalid.append(FIELD_LABELS.get(field_name, field_name))
        originator_invalid.extend(_validate_value(value, field_name, originator_field_rules.get(field_name, {})))
    if originator_missing or originator_invalid:
        originator_invalid = list(dict.fromkeys(originator_invalid))
        issues = []
        if originator_missing:
            issues.append(f"missing {', '.join(originator_missing)}")
        if originator_invalid:
            issues.append(f"invalid {', '.join(originator_invalid)}")
        errors.append(f"Originator profile: {'; '.join(issues)}")

    for payslip in payslips:
        profile = payslip.payroll_profile
        missing = []
        invalid = []
        for field_name in required_fields:
            value = getattr(profile, field_name, '') if profile else ''
            if not value:
                missing.append(FIELD_LABELS.get(field_name, field_name))
                continue
            pattern = FIELD_PATTERNS.get(field_name)
            if pattern and not pattern.match(str(value).upper()):
                invalid.append(FIELD_LABELS.get(field_name, field_name))
            invalid.extend(_validate_value(value, field_name, profile_field_rules.get(field_name, {})))
        if len((payslip.bank_payment_reference or '')) > reference_max_length:
            invalid.append(f'reference longer than {reference_max_length} characters')
        if reference_pattern and payslip.bank_payment_reference and not re.match(reference_pattern, payslip.bank_payment_reference):
            invalid.append('reference contains unsupported characters')
        if missing or invalid:
            invalid = list(dict.fromkeys(invalid))
            issues = []
            if missing:
                issues.append(f"missing {', '.join(missing)}")
            if invalid:
                issues.append(f"invalid {', '.join(invalid)}")
            errors.append(f"{payslip.staff_member.full_name}: {'; '.join(issues)}")

    if errors:
        raise ValueError(
            f"Bank export validation failed for {scheme['label']}: " + ' | '.join(errors)
        )