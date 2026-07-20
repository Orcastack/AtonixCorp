import unittest
from tempfile import TemporaryDirectory
from pathlib import Path

from atonixcorp_toolbox.audit import developer_audit_event
from atonixcorp_toolbox.crypto import decrypt_file, encrypt_file, sign_message, verify_message
from atonixcorp_toolbox.governance import GovernanceDocumentError, load_governance_yaml


class ToolboxTests(unittest.TestCase):
    def test_governance_document_requires_core_sections(self):
        with self.assertRaises(GovernanceDocumentError):
            load_governance_yaml("schema_version: 1\norganization: {}\n")

    def test_audit_event_redacts_credentials(self):
        event = developer_audit_event("sandbox.called", "Entity", "1", {"api_key": "secret", "name": "Sandbox"})
        self.assertEqual(event["metadata"]["api_key"], "[REDACTED]")
        self.assertEqual(event["metadata"]["name"], "Sandbox")

    def test_file_encryption_and_message_signing_detect_tampering(self):
        with TemporaryDirectory() as temporary_directory:
            source = Path(temporary_directory) / "source.txt"
            encrypted = Path(temporary_directory) / "encrypted.bin"
            restored = Path(temporary_directory) / "restored.txt"
            source.write_bytes(b"confidential governance message")
            encrypt_file(source, encrypted, secret="toolbox-test-secret", associated_data=b"governance")
            self.assertNotIn(source.read_bytes(), encrypted.read_bytes())
            decrypt_file(encrypted, restored, secret="toolbox-test-secret", associated_data=b"governance")
            self.assertEqual(restored.read_bytes(), source.read_bytes())

        signature = sign_message(b"approved", secret="toolbox-test-secret")
        self.assertTrue(verify_message(b"approved", signature, secret="toolbox-test-secret"))
        self.assertFalse(verify_message(b"tampered", signature, secret="toolbox-test-secret"))


if __name__ == "__main__":
    unittest.main()
