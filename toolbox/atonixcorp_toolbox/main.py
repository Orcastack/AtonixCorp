"""Small command toolbox for governance and DCI sandbox workflows."""
import json
from pathlib import Path

from atonixcorpsdk import AtonixCorpClient, Credentials

from .governance import GovernanceDocumentError, load_governance_yaml, sandbox_entity_fixture


def _usage():
    return "Usage: atonixcorp-toolbox <validate-governance|sandbox-entity> [arguments]"


def main(argv=None):
    import sys

    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        raise SystemExit(_usage())
    command = args.pop(0)
    if command == "validate-governance" and len(args) == 1:
        try:
            document = load_governance_yaml(Path(args[0]).read_text(encoding="utf-8"))
        except (OSError, GovernanceDocumentError) as error:
            raise SystemExit(f"Validation failed: {error}") from error
        print(json.dumps({"valid": True, "entities": len(document["entities"]), "schema_version": document["schema_version"]}))
        return
    if command == "sandbox-entity":
        organization_id = int(args[0]) if args else 1
        print(json.dumps(sandbox_entity_fixture(organization_id), indent=2))
        return
    raise SystemExit(_usage())


if __name__ == "__main__":
    main()
