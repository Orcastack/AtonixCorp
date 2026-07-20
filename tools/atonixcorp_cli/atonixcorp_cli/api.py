import json
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from . import __version__
from .errors import CLIError


DEFAULT_HOST = 'https://api.atonixcorp.com'
LOCAL_HOSTS = {'localhost', '127.0.0.1', '::1'}
REFRESH_BUFFER_SECONDS = 60


def expires_at_from_now(expires_in):
    return (datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))).isoformat()


def normalize_host(raw_host):
    candidate = (raw_host or DEFAULT_HOST).strip()
    if not candidate:
        raise CLIError('Host must not be empty.', 'INVALID_HOST')
    if '://' not in candidate:
        candidate = f'https://{candidate}'

    parsed = urlparse(candidate)
    if not parsed.hostname:
        raise CLIError('Host must include a valid network location.', 'INVALID_HOST')
    if parsed.scheme != 'https' and parsed.hostname not in LOCAL_HOSTS:
        raise CLIError('AtonixCorp CLI requires HTTPS for non-local hosts.', 'INSECURE_HOST')
    return candidate.rstrip('/')


class AtonixCorpClient:
    def __init__(self, host=None):
        self.host = normalize_host(host)
        self.user_agent = f'AtonixCorp-CLI/{__version__}'

    def _request_json(self, method, path, *, payload=None, access_token=None, organization_id=None):
        url = urljoin(f'{self.host}/', path.lstrip('/'))
        headers = {
            'User-Agent': self.user_agent,
            'Accept': 'application/json',
        }
        data = None
        if payload is not None:
            headers['Content-Type'] = 'application/json'
            data = json.dumps(payload).encode('utf-8')
        if access_token:
            headers['Authorization'] = f'Bearer {access_token}'
        if organization_id:
            headers['X-Organization-Id'] = organization_id

        request = Request(url, data=data, headers=headers, method=method.upper())
        try:
            with urlopen(request, timeout=30) as response:
                raw_body = response.read().decode('utf-8')
                return json.loads(raw_body) if raw_body else {}
        except HTTPError as exc:
            raw_body = exc.read().decode('utf-8', errors='replace') if hasattr(exc, 'read') else ''
            parsed = {}
            if raw_body:
                try:
                    parsed = json.loads(raw_body)
                except json.JSONDecodeError:
                    parsed = {}
            if isinstance(parsed, dict) and 'error' in parsed:
                error = parsed['error'] or {}
                raise CLIError(
                    error.get('message') or 'Request failed.',
                    error.get('code') or f'HTTP_{exc.code}',
                    status_code=exc.code,
                )
            raise CLIError(raw_body or 'Request failed.', f'HTTP_{exc.code}', status_code=exc.code)
        except URLError as exc:
            raise CLIError('Network request failed', 'NETWORK_ERROR') from exc

    def cli_login(self, api_key, organization_id):
        return self._request_json(
            'POST',
            '/auth/cli-login',
            payload={
                'api_key': api_key,
                'organization_id': organization_id,
            },
        )

    def refresh(self, api_key):
        return self._request_json('POST', '/auth/refresh', payload={'api_key': api_key})

    def me(self, access_token, organization_id):
        return self._request_json(
            'GET',
            '/auth/me',
            access_token=access_token,
            organization_id=organization_id,
        )

    def _token_is_stale(self, session):
        expires_at = session.get('expires_at')
        if not expires_at:
            return True
        try:
            expiry = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
        except ValueError:
            return True
        return expiry <= datetime.now(timezone.utc) + timedelta(seconds=REFRESH_BUFFER_SECONDS)

    def ensure_session(self, session):
        if not self._token_is_stale(session):
            return session

        refreshed = self.refresh(session['api_key'])
        session['access_token'] = refreshed['access_token']
        session['expires_at'] = expires_at_from_now(refreshed['expires_in'])
        session['organization_id'] = refreshed.get('organization_id', session['organization_id'])
        session['user'] = refreshed.get('user', session.get('user') or {})
        return session

    def request_with_session(self, method, path, session, *, payload=None):
        self.ensure_session(session)
        try:
            return self._request_json(
                method,
                path,
                payload=payload,
                access_token=session['access_token'],
                organization_id=session['organization_id'],
            )
        except CLIError as exc:
            if exc.status_code != 401:
                raise
            refreshed = self.refresh(session['api_key'])
            session['access_token'] = refreshed['access_token']
            session['expires_at'] = expires_at_from_now(refreshed['expires_in'])
            session['organization_id'] = refreshed.get('organization_id', session['organization_id'])
            session['user'] = refreshed.get('user', session.get('user') or {})
            return self._request_json(
                method,
                path,
                payload=payload,
                access_token=session['access_token'],
                organization_id=session['organization_id'],
            )