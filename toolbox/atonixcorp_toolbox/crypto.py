"""Portable AES-256-GCM and HMAC-SHA-256 helpers for developer tooling."""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
from pathlib import Path

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_FILE_PREFIX = b"atc-toolbox-aesgcm-v1:"


class CryptoOperationError(ValueError):
    """Raised when protected content fails authenticity or integrity checks."""


def _key_bytes(secret: str | bytes) -> bytes:
    raw = secret.encode("utf-8") if isinstance(secret, str) else secret
    try:
        decoded = base64.urlsafe_b64decode(raw + b"=" * (-len(raw) % 4))
        if len(decoded) == 32:
            return decoded
    except (ValueError, TypeError):
        pass
    return hashlib.sha256(raw).digest()


def encrypt_bytes(plaintext: bytes, *, secret: str | bytes, associated_data: bytes = b"") -> bytes:
    nonce = os.urandom(12)
    ciphertext = AESGCM(_key_bytes(secret)).encrypt(nonce, plaintext, associated_data)
    return _FILE_PREFIX + base64.urlsafe_b64encode(nonce + ciphertext)


def decrypt_bytes(envelope: bytes, *, secret: str | bytes, associated_data: bytes = b"") -> bytes:
    if not envelope.startswith(_FILE_PREFIX):
        raise CryptoOperationError("Unsupported encrypted file envelope.")
    try:
        packed = base64.urlsafe_b64decode(envelope[len(_FILE_PREFIX):])
        return AESGCM(_key_bytes(secret)).decrypt(packed[:12], packed[12:], associated_data)
    except (ValueError, InvalidTag) as error:
        raise CryptoOperationError("Encrypted content failed integrity verification.") from error


def encrypt_file(source: str | Path, destination: str | Path, *, secret: str | bytes, associated_data: bytes = b"") -> None:
    Path(destination).write_bytes(encrypt_bytes(Path(source).read_bytes(), secret=secret, associated_data=associated_data))


def decrypt_file(source: str | Path, destination: str | Path, *, secret: str | bytes, associated_data: bytes = b"") -> None:
    Path(destination).write_bytes(decrypt_bytes(Path(source).read_bytes(), secret=secret, associated_data=associated_data))


def sign_message(message: bytes, *, secret: str | bytes) -> str:
    return hmac.new(_key_bytes(secret), message, hashlib.sha256).hexdigest()


def verify_message(message: bytes, signature: str, *, secret: str | bytes) -> bool:
    return hmac.compare_digest(sign_message(message, secret=secret), signature)
