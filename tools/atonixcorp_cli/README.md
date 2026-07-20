# AtonixCorp CLI

Python implementation of the `atonixcorp` command for API-key based AtonixCorp authentication.

Install with repo bootstrap:

```bash
./setup.sh
```

Or install locally without the full app bootstrap:

```bash
cd tools/atonixcorp_cli
/home/atonixdev/legdora/api/.venv/bin/python -m pip install -e .
```

Core commands:

```bash
atonixcorp login --api-key <API_KEY> --org <ORGANIZATION_ID>
atonixcorp whoami
atonixcorp use <PROFILE>
atonixcorp logout
atonixcorp organizations list
atonixcorp accounts list
atonixcorp customers list
atonixcorp vendors list
atonixcorp reports trial-balance --as-of-date 2026-03-31
```