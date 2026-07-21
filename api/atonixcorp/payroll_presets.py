from decimal import Decimal


DEFAULT_PRESET = {
    'income_tax_rate': Decimal('0.1000'),
    'employee_tax_rate': Decimal('0.0000'),
    'employer_tax_rate': Decimal('0.0000'),
    'bank_file_format': 'csv',
    'bank_institution': 'generic',
    'bank_export_variant': 'standard',
    'statutory_jurisdiction': 'Generic',
}

SEPA_COUNTRIES = {'AT', 'BE', 'DE', 'ES', 'FR', 'IE', 'IT', 'NL', 'PT'}

COUNTRY_PAYROLL_PRESETS = {
    'US': {
        'income_tax_rate': Decimal('0.1000'),
        'employee_tax_rate': Decimal('0.0500'),
        'employer_tax_rate': Decimal('0.0750'),
        'bank_file_format': 'aba',
        'bank_institution': 'wells_fargo',
        'bank_export_variant': 'ppd',
        'statutory_jurisdiction': 'US Federal',
    },
    'GB': {
        'income_tax_rate': Decimal('0.1200'),
        'employee_tax_rate': Decimal('0.0200'),
        'employer_tax_rate': Decimal('0.1380'),
        'bank_file_format': 'bacs',
        'bank_institution': 'barclays',
        'bank_export_variant': 'standard',
        'statutory_jurisdiction': 'HMRC',
    },
    'CA': {
        'income_tax_rate': Decimal('0.1100'),
        'employee_tax_rate': Decimal('0.0350'),
        'employer_tax_rate': Decimal('0.0450'),
        'bank_file_format': 'csv',
        'bank_institution': 'adp',
        'bank_export_variant': 'workforce_now',
        'statutory_jurisdiction': 'CRA',
    },
    'NG': {
        'income_tax_rate': Decimal('0.0700'),
        'employee_tax_rate': Decimal('0.0800'),
        'employer_tax_rate': Decimal('0.1000'),
        'bank_file_format': 'csv',
        'bank_institution': 'generic',
        'bank_export_variant': 'standard',
        'statutory_jurisdiction': 'FIRS',
    },
}


def get_payroll_country_preset(country_code):
    code = (country_code or '').upper().strip()
    preset = dict(DEFAULT_PRESET)
    if code in SEPA_COUNTRIES:
        preset.update({
            'income_tax_rate': Decimal('0.1200'),
            'employee_tax_rate': Decimal('0.0400'),
            'employer_tax_rate': Decimal('0.0850'),
            'bank_file_format': 'sepa',
            'bank_institution': 'deutsche_bank',
            'bank_export_variant': 'pain.001.001.03',
            'statutory_jurisdiction': f'{code} Payroll Authority',
        })
    preset.update(COUNTRY_PAYROLL_PRESETS.get(code, {}))
    preset['country_code'] = code or 'DEFAULT'
    return preset


def list_payroll_country_presets():
    supported = sorted(SEPA_COUNTRIES | set(COUNTRY_PAYROLL_PRESETS.keys()))
    return [get_payroll_country_preset(code) for code in supported]


def resolve_bank_file_format(country_code, preferred_format=''):
    return preferred_format or get_payroll_country_preset(country_code).get('bank_file_format', 'csv')


def resolve_bank_institution(country_code, preferred_institution=''):
    return preferred_institution or get_payroll_country_preset(country_code).get('bank_institution', 'generic')


def resolve_bank_export_variant(country_code, preferred_variant=''):
    return preferred_variant or get_payroll_country_preset(country_code).get('bank_export_variant', 'standard')