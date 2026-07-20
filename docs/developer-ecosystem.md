# AtonixCorp CLI, SDK, and Toolbox

## Repository Layout

- `atonixcorpsdk`: Official Python SDK for Developer Console Integration (DCI).
- `atonixcorpcli`: Click-based command line client for developer and governance operations.
- `toolbox`: Lightweight validation, sandbox fixture, and audit-diagnostic utilities.

Install locally in dependency order:

```bash
python3 -m pip install -e ./atonixcorpsdk
python3 -m pip install -e ./atonixcorpcli
python3 -m pip install -e ./toolbox
```

## DCI Connection Model

The SDK defaults to the local sandbox at `http://localhost:8000`. It connects to:

- `/auth/cli-login` for API-key exchange into a short-lived DCI Bearer token.
- `/api/entities/` and `/api/entity-departments/` for enterprise identity and departments.
- `/api/v1/workspaces/...` for workspace operations, meetings, and encrypted file transfer.
- `/api/entities/{entity_id}/equity/...` for equity registry operations.
- `/v1/...` for the published developer API and OpenAPI documentation.

Use `AtonixCorpClient(base_url="https://api.atonixcorp.com")` only with a production-issued credential. The SDK rejects plain HTTP except for the explicit loopback sandbox URL. No SDK, CLI, or toolbox command persists API keys, OAuth tokens, or client secrets.

## Sandbox Examples

```bash
atonixcorp sandbox-status
atonixcorp entity create --organization-id 1 --name "Sandbox Holdings" --country US --department finance --department equity_governance
atonixcorp workspace create --name "Sandbox Finance" --linked-entity-id 1
atonixcorp-toolbox sandbox-entity 1
```

Entity creation carries department selections to the governed backend workflow, which provisions entity departments, mirrors workspace groups, writes audit events, and retains the configuration in governance YAML.

## File and OAuth Security

Workspace binary uploads use AES-256-GCM before persistence and are downloaded only after workspace authorization. Configure `WORKSPACE_FILE_ENCRYPTION_KEY` and an S3 Django storage backend in production. Governance YAML exports are HMAC-SHA-256 signed and imports reject unsigned or modified documents; configure `GOVERNANCE_SIGNING_KEY` in the deployment secret manager.

The toolbox also exposes `encrypt_file`, `decrypt_file`, `sign_message`, and `verify_message` from `atonixcorp_toolbox.crypto`. Supply encryption/signing keys from a secret manager or protected environment variable; the toolbox never generates or stores them on a user's behalf.

Google Drive and OneDrive exports receive a short-lived access token only for the export request; S3 exports receive a short-lived HTTPS pre-signed upload URL. Configure the respective tenant client secrets and redirect URIs only in the deployment secret manager.
