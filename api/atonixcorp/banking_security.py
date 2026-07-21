import base64
import hashlib
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from django.conf import settings


_ENCODING = 'utf-8'
_VERSION_PREFIX = 'v1'
_NONCE_SIZE = 12


def _banking_encryption_key():
    configured_key = getattr(settings, 'BANKING_TOKEN_ENCRYPTION_KEY', '') or os.getenv('BANKING_TOKEN_ENCRYPTION_KEY', '')
    key_material = configured_key or f"lgx-banking::{settings.SECRET_KEY}"
    if isinstance(key_material, str):
        key_material = key_material.encode(_ENCODING)
    return hashlib.sha256(key_material).digest()


def encrypt_secret(value):
    if not value:
        return ''

    nonce = os.urandom(_NONCE_SIZE)
    ciphertext = AESGCM(_banking_encryption_key()).encrypt(nonce, value.encode(_ENCODING), None)
    token = base64.urlsafe_b64encode(nonce + ciphertext).decode(_ENCODING)
    return f'{_VERSION_PREFIX}:{token}'


def decrypt_secret(value):
    if not value:
        return ''

    if not value.startswith(f'{_VERSION_PREFIX}:'):
        return value

    encoded = value.split(':', 1)[1]
    payload = base64.urlsafe_b64decode(encoded.encode(_ENCODING))
    nonce = payload[:_NONCE_SIZE]
    ciphertext = payload[_NONCE_SIZE:]
    plaintext = AESGCM(_banking_encryption_key()).decrypt(nonce, ciphertext, None)
    return plaintext.decode(_ENCODING)


def mask_secret(value, prefix=4, suffix=4):
    if not value:
        return ''
    if len(value) <= prefix + suffix:
        return '*' * len(value)
    return f'{value[:prefix]}{"*" * max(4, len(value) - prefix - suffix)}{value[-suffix:]}'