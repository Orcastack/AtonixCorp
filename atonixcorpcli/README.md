# AtonixCorp CLI

Click-based client for AtonixCorp Developer Console Integration.

```bash
pip install -e ../atonixcorpsdk -e .
atonixcorp --url http://localhost:8000 login --organization-id org_1 --api-key "$ATONIXCORP_API_KEY"
atonixcorp entity create --organization-id 1 --name "Sandbox Holdings" --country US --department finance
atonixcorp workspace create --name "Finance Operations" --linked-entity-id 1
```

Commands return JSON by default and surface API errors without leaking request credentials.
