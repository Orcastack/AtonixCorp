"""Company identity validation shared by registration APIs and persistence."""
from __future__ import annotations

import re

from django.core.exceptions import ValidationError


_REGISTRATION_NUMBER_PATTERN = re.compile(r'^[A-Za-z0-9][A-Za-z0-9 ._/-]*$')
_REGISTRATION_NUMBER_SEPARATORS = re.compile(r'[ ._/-]+')


def normalize_registration_number(value):
    """Return the canonical registry identifier used for company identity."""
    raw_value = str(value or '').strip()
    if not raw_value:
        raise ValidationError('Company registration number is required.')
    if not _REGISTRATION_NUMBER_PATTERN.fullmatch(raw_value):
        raise ValidationError('Company registration number contains unsupported characters.')

    normalized = _REGISTRATION_NUMBER_SEPARATORS.sub('', raw_value).upper()
    if not 4 <= len(normalized) <= 64 or not any(character.isdigit() for character in normalized):
        raise ValidationError('Company registration number must contain 4-64 letters or digits and include a digit.')
    return normalized