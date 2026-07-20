"""Audit helpers that keep credentials and personally sensitive values out of diagnostics."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone

SENSITIVE_KEYS = {"access_token", "api_key", "authorization", "password", "client_secret", "oauth_access_token"}


def redact(value):
    if isinstance(value, dict):
        return {key: "[REDACTED]" if key.lower() in SENSITIVE_KEYS else redact(item) for key, item in value.items()}
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


def developer_audit_event(action: str, resource_type: str, resource_id: str, metadata: dict | None = None) -> dict:
    return {
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "resource_type": resource_type,
        "resource_id": str(resource_id),
        "metadata": redact(metadata or {}),
    }
