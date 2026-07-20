# Pre-Deployment Readiness - 2026-07-20

## Validated Workflows

- Entity, equity, and workspace creation are covered by the enterprise API suite, including organization ownership, entity access scope, department provisioning, governance audit events, and YAML department export.
- Equity endpoints now resolve their entity through the authenticated enterprise access scope. A user without access receives `404` from equity scenario endpoints and cannot export or simulate data for another organization.
- Workspace department controls enforce entity/workspace roles, and department mutations are audited.
- Workspace file and folder metadata rejects traversal-style names (`.`, `..`, `/`, `\\`, and null bytes) before persistence. Upload/delete actions continue to use workspace audit logging.
- Meeting scheduling validates start/end times and uses workspace role enforcement for meeting management. Calendar event CRUD is independently role-protected and audited through workspace logs.
- The scheduled reporting-pack workflow test is isolated from setup mail and confirms exactly one intended delivery with its PDF artifact.

## Test Evidence

```text
python manage.py check
System check identified no issues (0 silenced).

python manage.py test finances workspaces equity --verbosity 1
Ran 107 tests in 43.061s
OK

npm test -- --watchAll=false --passWithNoTests
1 suite passed; 1 test passed

npm run build
Compiled successfully with existing unrelated ESLint warnings.
```

## Deployment Configuration Boundaries

- Workspace file uploads now encrypt binary content before writing to the configured Django storage backend and expose authenticated downloads. Set `WORKSPACE_FILE_ENCRYPTION_KEY` and configure `WORKSPACE_FILE_STORAGE_BACKEND=storages.backends.s3.S3Storage` plus the AWS variables for S3 production storage. The object store should enforce server-side encryption and private bucket access as a second storage-layer control.
- Google Drive, OneDrive, and AWS S3 integrations require tenant OAuth applications, redirect URLs, scoped credentials, key rotation, and a provider-specific integration test account. The governance cloud-export flow must be tested with non-production fixtures before production credentials are introduced.
- Browser/device smoke testing requires authenticated test accounts with owner, administrator, member, and viewer roles. Create them for a test organization with:

```text
python manage.py create_smoke_test_accounts --organization-id <id>
```

The command securely prompts for a temporary password, updates the organization owner password, and provisions CFO, finance analyst, and viewer members. Do not commit test credentials or place them in automation logs.