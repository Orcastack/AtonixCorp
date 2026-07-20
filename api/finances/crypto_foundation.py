"""Versioned application-layer cryptography for protected AtonixCorp records.

Keys are supplied only through deployment secrets. AES-GCM associated data binds
ciphertext to its owning resource; HMAC signatures make portable governance
configuration tamper-evident.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from typing import Any

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from django.conf import settings
from rest_framework.exceptions import ValidationError

AES_GCM_PREFIX = b"atc-aesgcm-v1:"
GOVERNANCE_SIGNATURE_ALGORITHM = "HMAC-SHA256"
GOVERNANCE_SIGNATURE_KEY_ID = "governance-hmac-v1"


def _secret_bytes(setting_name: str) -> bytes:
    configured = getattr(settings, setting_name, "") or os.getenv(setting_name, "")
    if not configured:
        if not settings.DEBUG:
            raise RuntimeError(f"{setting_name} is required when DJANGO_DEBUG is false.")
        configured = settings.SECRET_KEY
    raw = configured.encode("utf-8") if isinstance(configured, str) else configured
    try:
        decoded = base64.urlsafe_b64decode(raw + b"=" * (-len(raw) % 4))
        if len(decoded) == 32:
            return decoded
    except (ValueError, TypeError):
        pass
    return hashlib.sha256(raw).digest()


def encrypt_aes_gcm(plaintext: bytes, *, associated_data: bytes, key_setting: str = "WORKSPACE_FILE_ENCRYPTION_KEY") -> bytes:
    nonce = os.urandom(12)
    ciphertext = AESGCM(_secret_bytes(key_setting)).encrypt(nonce, plaintext, associated_data)
    return AES_GCM_PREFIX + base64.urlsafe_b64encode(nonce + ciphertext)


def decrypt_aes_gcm(value: bytes, *, associated_data: bytes, key_setting: str = "WORKSPACE_FILE_ENCRYPTION_KEY") -> bytes:
    if not value.startswith(AES_GCM_PREFIX):
        raise ValueError("Unsupported AES-GCM envelope version.")
    try:
        packed = base64.urlsafe_b64decode(value[len(AES_GCM_PREFIX):])
        return AESGCM(_secret_bytes(key_setting)).decrypt(packed[:12], packed[12:], associated_data)
    except (ValueError, InvalidTag) as error:
        raise ValidationError({"content": "Encrypted content failed integrity verification."}) from error


def canonical_governance_payload(document: dict[str, Any]) -> bytes:
    unsigned = dict(document)
    unsigned.pop("integrity", None)
    return json.dumps(unsigned, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def sign_governance_document(document: dict[str, Any]) -> dict[str, str]:
    payload = canonical_governance_payload(document)
    return {
        "algorithm": GOVERNANCE_SIGNATURE_ALGORITHM,
        "key_id": GOVERNANCE_SIGNATURE_KEY_ID,
        "checksum": hashlib.sha256(payload).hexdigest(),
        "signature": hmac.new(_secret_bytes("GOVERNANCE_SIGNING_KEY"), payload, hashlib.sha256).hexdigest(),
    }


def verify_governance_document(document: dict[str, Any]) -> None:
    integrity = document.get("integrity")
    if not isinstance(integrity, dict):
        raise ValidationError({"integrity": "Signed governance integrity metadata is required."})
    payload = canonical_governance_payload(document)
    checksum = hashlib.sha256(payload).hexdigest()
    expected_signature = hmac.new(_secret_bytes("GOVERNANCE_SIGNING_KEY"), payload, hashlib.sha256).hexdigest()
    if integrity.get("algorithm") != GOVERNANCE_SIGNATURE_ALGORITHM or integrity.get("key_id") != GOVERNANCE_SIGNATURE_KEY_ID:
        raise ValidationError({"integrity": "Unsupported governance signature metadata."})
    if not hmac.compare_digest(str(integrity.get("checksum", "")), checksum):
        raise ValidationError({"integrity": "Governance checksum verification failed."})
    if not hmac.compare_digest(str(integrity.get("signature", "")), expected_signature):
        raise ValidationError({"integrity": "Governance signature verification failed."})
