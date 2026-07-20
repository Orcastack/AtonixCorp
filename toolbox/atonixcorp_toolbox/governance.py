"""Governance YAML validation and sandbox fixture helpers."""
from __future__ import annotations

import yaml


class GovernanceDocumentError(ValueError):
    pass


def load_governance_yaml(content: str) -> dict:
    document = yaml.safe_load(content)
    if not isinstance(document, dict):
        raise GovernanceDocumentError("Governance YAML must contain an object at its root.")
    required = {"schema_version", "organization", "entities"}
    missing = required.difference(document)
    if missing:
        raise GovernanceDocumentError(f"Governance YAML is missing: {', '.join(sorted(missing))}.")
    if not isinstance(document["entities"], list):
        raise GovernanceDocumentError("Governance YAML entities must be a list.")
    return document


def sandbox_entity_fixture(organization_id: int = 1) -> dict:
    return {
        "organization_id": organization_id,
        "name": "Sandbox Holdings",
        "country": "US",
        "entity_type": "corporation",
        "workspace_mode": "combined",
        "department_selections": ["finance", "legal_compliance", "equity_governance"],
    }
