import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from unittest.mock import patch

from atonixcorp_cli.api import AtonixCorpClient, expires_at_from_now
from atonixcorp_cli.errors import CLIError
from atonixcorp_cli.main import main
from atonixcorp_cli.storage import upsert_profile


class CLITestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        os.environ['ATONIXCORP_CLI_CONFIG_DIR'] = self.temp_dir.name
        os.environ['ATONIXCORP_CLI_DISABLE_KEYRING'] = '1'

    def tearDown(self):
        os.environ.pop('ATONIXCORP_CLI_CONFIG_DIR', None)
        os.environ.pop('ATONIXCORP_CLI_DISABLE_KEYRING', None)
        self.temp_dir.cleanup()

    def test_login_stores_encrypted_profile(self):
        with patch.object(AtonixCorpClient, 'cli_login', return_value={
            'access_token': 'access-token-123',
            'expires_in': 3600,
            'organization_id': 'org_123',
            'user': {'id': 'user_1', 'email': 'dev@example.com', 'role': 'developer'},
        }), patch.object(AtonixCorpClient, 'me', return_value={
            'organization': {'id': 'org_123', 'name': 'AtonixCorp Demo LLC'},
            'user': {'id': 'user_1', 'email': 'dev@example.com', 'role': 'developer'},
            'session': {'expires_at': expires_at_from_now(3600)},
        }):
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                exit_code = main(['login', '--api-key', 'cli_123.secret_456', '--org', 'org_123', '--profile', 'prod'])

        self.assertEqual(exit_code, 0)
        config_path = os.path.join(self.temp_dir.name, 'config.json')
        with open(config_path, 'r', encoding='utf-8') as handle:
            config = json.load(handle)
        stored = config['profiles']['prod']
        self.assertNotIn('access-token-123', json.dumps(stored))
        self.assertNotIn('cli_123.secret_456', json.dumps(stored))
        self.assertIn('Successfully logged in to AtonixCorp', stdout.getvalue())

    def test_request_with_session_refreshes_expired_token(self):
        client = AtonixCorpClient('https://api.example.com')
        session = {
            'profile': 'default',
            'host': 'https://api.example.com',
            'organization_id': 'org_123',
            'access_token': 'expired-token',
            'api_key': 'cli_123.secret_456',
            'expires_at': '2000-01-01T00:00:00+00:00',
            'user': {},
        }

        calls = []

        def fake_request(method, path, **kwargs):
            calls.append((method, path, kwargs))
            if path == '/auth/refresh':
                return {
                    'access_token': 'fresh-token',
                    'expires_in': 3600,
                    'organization_id': 'org_123',
                    'user': {'email': 'dev@example.com'},
                }
            if kwargs.get('access_token') == 'fresh-token':
                return {'ok': True}
            raise CLIError('Unauthorized', 'UNAUTHORIZED', status_code=401)

        with patch.object(client, '_request_json', side_effect=fake_request):
            response = client.request_with_session('GET', '/auth/me', session)

        self.assertEqual(response, {'ok': True})
        self.assertEqual(session['access_token'], 'fresh-token')
        self.assertEqual(calls[0][1], '/auth/refresh')

    def test_invalid_input_uses_standard_error_output(self):
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            exit_code = main(['login', '--org', 'org_123'])

        self.assertEqual(exit_code, 1)
        self.assertIn('Error: Missing required flags. Use --api-key and --org.', stderr.getvalue())
        self.assertIn('Code: INVALID_INPUT', stderr.getvalue())

    def test_accounts_list_uses_authenticated_session(self):
        upsert_profile(
            'prod',
            {
                'host': 'https://api.example.com',
                'organization_id': 'org_123',
                'organization_name': 'AtonixCorp Demo LLC',
                'access_token': 'access-token-123',
                'api_key': 'cli_123.secret_456',
                'expires_at': expires_at_from_now(3600),
                'user': {'email': 'dev@example.com'},
            },
            make_current=True,
        )

        stdout = io.StringIO()
        with patch.object(AtonixCorpClient, 'request_with_session', return_value=[{'id': 'acc_1', 'name': 'Cash'}]):
            with redirect_stdout(stdout):
                exit_code = main(['accounts', 'list', '--profile', 'prod'])

        self.assertEqual(exit_code, 0)
        self.assertIn('"id": "acc_1"', stdout.getvalue())
        self.assertIn('"name": "Cash"', stdout.getvalue())

    def test_report_command_builds_query_string(self):
        upsert_profile(
            'prod',
            {
                'host': 'https://api.example.com',
                'organization_id': 'org_123',
                'organization_name': 'AtonixCorp Demo LLC',
                'access_token': 'access-token-123',
                'api_key': 'cli_123.secret_456',
                'expires_at': expires_at_from_now(3600),
                'user': {'email': 'dev@example.com'},
            },
            make_current=True,
        )

        stdout = io.StringIO()
        with patch.object(AtonixCorpClient, 'request_with_session', return_value={'ok': True}) as mocked_request:
            with redirect_stdout(stdout):
                exit_code = main([
                    'reports',
                    'profit-and-loss',
                    '--profile', 'prod',
                    '--from-date', '2026-03-01',
                    '--to-date', '2026-03-31',
                    '--currency', 'USD',
                ])

        self.assertEqual(exit_code, 0)
        self.assertEqual(mocked_request.call_args.args[0], 'GET')
        self.assertIn('/v1/reports/profit-and-loss?', mocked_request.call_args.args[1])
        self.assertIn('from_date=2026-03-01', mocked_request.call_args.args[1])
        self.assertIn('to_date=2026-03-31', mocked_request.call_args.args[1])
        self.assertIn('currency=USD', mocked_request.call_args.args[1])