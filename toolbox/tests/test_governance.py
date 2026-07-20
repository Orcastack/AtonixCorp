import unittest

from atonixcorp_toolbox.audit import developer_audit_event
from atonixcorp_toolbox.governance import GovernanceDocumentError, load_governance_yaml


class ToolboxTests(unittest.TestCase):
    def test_governance_document_requires_core_sections(self):
        with self.assertRaises(GovernanceDocumentError):
            load_governance_yaml("schema_version: 1\norganization: {}\n")

    def test_audit_event_redacts_credentials(self):
        event = developer_audit_event("sandbox.called", "Entity", "1", {"api_key": "secret", "name": "Sandbox"})
        self.assertEqual(event["metadata"]["api_key"], "[REDACTED]")
        self.assertEqual(event["metadata"]["name"], "Sandbox")


if __name__ == "__main__":
    unittest.main()
