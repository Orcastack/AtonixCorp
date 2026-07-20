import unittest
from unittest.mock import MagicMock, patch

from atonixcorpsdk import AtonixCorpClient, Credentials


class _Response:
    headers = {"Content-Type": "application/json"}

    def __init__(self, body):
        self.body = body

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class ClientTests(unittest.TestCase):
    @patch("atonixcorpsdk.client.urlopen")
    def test_entity_creation_uses_bearer_auth_and_enterprise_endpoint(self, mocked_urlopen):
        mocked_urlopen.return_value = _Response(b'{"id": 42, "name": "Sandbox Entity"}')
        client = AtonixCorpClient.sandbox(credentials=Credentials(access_token="token"))

        result = client.create_entity({"organization_id": 1, "name": "Sandbox Entity"})

        request = mocked_urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "http://localhost:8000/api/entities/")
        self.assertEqual(request.get_header("Authorization"), "Bearer token")
        self.assertEqual(result["id"], 42)

    def test_non_local_plain_http_endpoint_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "require an HTTPS endpoint"):
            AtonixCorpClient(base_url="http://api.example.test")


if __name__ == "__main__":
    unittest.main()
