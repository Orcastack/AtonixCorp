"""Provider adapters for portable governance YAML exports.

OAuth tokens and S3 pre-signed URLs are request-only inputs and are never
persisted in export records or audit metadata.
"""
from __future__ import annotations

import hashlib
import json
import re
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlparse, urlunparse
from urllib.request import Request, urlopen

from rest_framework.exceptions import ValidationError

from .governance_configurations import render_governance_yaml
from .models import GovernanceCloudExport


_FILENAME_PATTERN = re.compile(r'[^A-Za-z0-9._-]+')


def _safe_filename(value, organization):
    default_name = f'{organization.slug or organization.id}-governance.yml'
    filename = _FILENAME_PATTERN.sub('-', str(value or default_name).strip()).strip('.-')
    if not filename:
        filename = default_name
    if not filename.endswith(('.yml', '.yaml')):
        filename = f'{filename}.yml'
    return filename[:255]


def _request(url, *, method='GET', headers=None, body=None):
    request = Request(url, data=body, headers=headers or {}, method=method)
    try:
        with urlopen(request, timeout=20) as response:
            return response.read(), response.headers
    except HTTPError as error:
        if error.code == 404 and method == 'GET':
            return b'', None
        raise ValidationError({'destination': f'Cloud provider rejected the export ({error.code}).'}) from error
    except URLError as error:
        raise ValidationError({'destination': 'Cloud provider could not be reached over TLS.'}) from error


def _json_request(url, *, method='GET', headers=None, body=None):
    response_body, _ = _request(url, method=method, headers=headers, body=body)
    try:
        return json.loads(response_body.decode('utf-8') or '{}')
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValidationError({'destination': 'Cloud provider returned an invalid response.'}) from error


def _oauth_token(payload):
    token = str(payload.get('oauth_access_token') or '').strip()
    if not token:
        raise ValidationError({'oauth_access_token': 'An OAuth access token is required for this destination.'})
    return token


def _export_google_drive(content, filename, payload, overwrite):
    token = _oauth_token(payload)
    folder_id = str(payload.get('folder_id') or '').strip()
    escaped_filename = filename.replace("'", "\\'")
    query = f"name = '{escaped_filename}' and trashed = false"
    if folder_id:
        query += f" and '{folder_id}' in parents"
    search_url = f'https://www.googleapis.com/drive/v3/files?{urlencode({"q": query, "fields": "files(id,name,webViewLink)"})}'
    headers = {'Authorization': f'Bearer {token}'}
    existing = _json_request(search_url, headers=headers).get('files', [])
    if existing and not overwrite:
        raise ValidationError({'destination': 'A file with this name already exists in Google Drive. Confirm overwrite to replace it.'})

    metadata = {'name': filename}
    if folder_id:
        metadata['parents'] = [folder_id]
    boundary = 'atonixcorp-governance-export'
    body = (
        f'--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n'.encode('utf-8')
        + json.dumps(metadata).encode('utf-8')
        + f'\r\n--{boundary}\r\nContent-Type: application/x-yaml\r\n\r\n'.encode('utf-8')
        + content
        + f'\r\n--{boundary}--\r\n'.encode('utf-8')
    )
    method = 'PATCH' if existing else 'POST'
    file_path = f'/{existing[0]["id"]}' if existing else ''
    result = _json_request(
        f'https://www.googleapis.com/upload/drive/v3/files{file_path}?uploadType=multipart&fields=id,webViewLink,name',
        method=method,
        headers={**headers, 'Content-Type': f'multipart/related; boundary={boundary}'},
        body=body,
    )
    return result.get('webViewLink') or result.get('id', ''), f'Google Drive/{folder_id or "root"}'


def _export_onedrive(content, filename, payload, overwrite):
    token = _oauth_token(payload)
    raw_path = str(payload.get('path') or 'AtonixCorp').strip().strip('/')
    if '..' in raw_path.split('/'):
        raise ValidationError({'path': 'OneDrive path cannot contain parent traversal.'})
    target_path = '/'.join(part for part in [raw_path, filename] if part)
    conflict_behavior = 'replace' if overwrite else 'fail'
    endpoint = (
        f'https://graph.microsoft.com/v1.0/me/drive/root:/{quote(target_path)}:/content?'
        f'{urlencode({"@microsoft.graph.conflictBehavior": conflict_behavior})}'
    )
    result = _json_request(
        endpoint,
        method='PUT',
        headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/x-yaml'},
        body=content,
    )
    return result.get('webUrl') or result.get('id', ''), f'OneDrive/{raw_path or "root"}'


def _export_s3(content, payload, overwrite):
    presigned_url = str(payload.get('presigned_url') or '').strip()
    parsed_url = urlparse(presigned_url)
    if parsed_url.scheme != 'https' or not parsed_url.hostname or 'amazonaws.com' not in parsed_url.hostname:
        raise ValidationError({'presigned_url': 'Provide an HTTPS AWS S3 pre-signed upload URL.'})
    headers = {'Content-Type': 'application/x-yaml'}
    if not overwrite:
        headers['If-None-Match'] = '*'
    _request(presigned_url, method='PUT', headers=headers, body=content)
    remote_reference = urlunparse((parsed_url.scheme, parsed_url.netloc, parsed_url.path, '', '', ''))
    return remote_reference, remote_reference


def export_governance_yaml(organization, requested_by, payload):
    provider = str(payload.get('provider') or '').strip()
    if provider not in {'google_drive', 'onedrive', 'aws_s3'}:
        raise ValidationError({'provider': 'Choose Google Drive, OneDrive, or AWS S3.'})
    overwrite = bool(payload.get('overwrite', False))
    filename = _safe_filename(payload.get('file_name'), organization)
    content = render_governance_yaml(organization).encode('utf-8')
    checksum = hashlib.sha256(content).hexdigest()

    try:
        if provider == 'google_drive':
            remote_reference, destination = _export_google_drive(content, filename, payload, overwrite)
        elif provider == 'onedrive':
            remote_reference, destination = _export_onedrive(content, filename, payload, overwrite)
        else:
            remote_reference, destination = _export_s3(content, payload, overwrite)
    except ValidationError as error:
        GovernanceCloudExport.objects.create(
            organization=organization,
            requested_by=requested_by,
            provider=provider,
            status='failed',
            file_name=filename,
            checksum=checksum,
            destination=str(payload.get('path') or payload.get('folder_id') or 'AWS S3')[:500],
            overwrite_confirmed=overwrite,
            error_message=str(error.detail)[:500],
        )
        raise

    return GovernanceCloudExport.objects.create(
        organization=organization,
        requested_by=requested_by,
        provider=provider,
        status='completed',
        file_name=filename,
        checksum=checksum,
        destination=destination,
        remote_reference=remote_reference[:500],
        overwrite_confirmed=overwrite,
    )