# Governance Cloud Export

A company owner can export the current governance YAML through Organization Settings. Local download is always available. Cloud exports are recorded in `GovernanceCloudExport` and in the platform audit trail.

## API

- `GET /api/organizations/{id}/export_governance_yaml/` downloads the YAML locally.
- `POST /api/organizations/{id}/export_governance_cloud/` sends YAML to a cloud provider.
- `GET /api/organizations/{id}/governance_cloud_exports/` returns the latest 50 delivery records.

All endpoints require the organization owner. The organization queryset prevents users outside the company from discovering or exporting its configuration.

## Provider Requests

Google Drive request fields:

```json
{
  "provider": "google_drive",
  "oauth_access_token": "provider-issued access token",
  "folder_id": "optional Drive folder ID",
  "file_name": "governance.yml",
  "overwrite": false
}
```

OneDrive request fields:

```json
{
  "provider": "onedrive",
  "oauth_access_token": "provider-issued Microsoft Graph token",
  "path": "AtonixCorp",
  "file_name": "governance.yml",
  "overwrite": false
}
```

AWS S3 request fields:

```json
{
  "provider": "aws_s3",
  "presigned_url": "https://bucket.s3.amazonaws.com/path/governance.yml?...",
  "overwrite": false
}
```

## Security Rules

- Google and Microsoft access tokens are OAuth bearer tokens and are used only for the active request. They are never stored in database records, YAML, or audit metadata.
- S3 uploads use an HTTPS pre-signed URL. AWS access keys and bucket credentials are never accepted or stored by AtonixCorp.
- Google Drive checks for an existing filename and refuses to replace it unless `overwrite` is true. OneDrive uses Microsoft Graph conflict behavior, and S3 sends `If-None-Match: *` unless replacement is confirmed.
- Every completed and failed cloud attempt creates a delivery record. Successful local and cloud deliveries also create a platform audit event with provider, destination, checksum, user, and timestamp.
- Provider APIs are contacted only over HTTPS. Configure Google OAuth scopes for Drive file creation and Microsoft Graph scopes for OneDrive file creation before issuing tokens to users.

## External Provider Testing

Automated tests mock provider calls to verify payload handling, secret redaction, overwrite behavior, audit records, and company access control. Run a separate staging test with tenant-specific OAuth clients and a disposable S3 bucket before enabling production credentials.