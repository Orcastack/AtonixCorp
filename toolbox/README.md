# AtonixCorp Toolbox

Small utilities for AtonixCorp governance and DCI sandbox development.

```bash
pip install -e ../atonixcorpsdk -e .
atonixcorp-toolbox sandbox-entity 1
atonixcorp-toolbox validate-governance ./governance.yml
```

The `atonixcorp_toolbox.audit` module creates redacted diagnostic events. It never writes API keys, OAuth tokens, passwords, or client secrets into output metadata.
