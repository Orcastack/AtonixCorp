# Ledgora CLI

Python implementation of the `ledgora` command for API-key based Ledgora authentication.

Install with repo bootstrap:

```bash
./setup.sh
```

Or install locally without the full app bootstrap:

```bash
cd tools/ledgora_cli
/home/atonixdev/legdora/api/.venv/bin/python -m pip install -e .
```

Core commands:

```bash
ledgora login --api-key <API_KEY> --org <ORGANIZATION_ID>
ledgora whoami
ledgora use <PROFILE>
ledgora logout
ledgora organizations list
ledgora accounts list
ledgora customers list
ledgora vendors list
ledgora reports trial-balance --as-of-date 2026-03-31
```