# AtonixCorp macOS DMG

This project creates a signed and notarized macOS 13+ DMG containing the AtonixCorp developer toolchain: `atonixcorpcli`, `atonixcorpsdk`, and toolbox utilities.

Run only on a macOS release runner:

```bash
export VERSION=0.1.0
export APPLE_SIGNING_IDENTITY="Developer ID Application: AtonixCorp (TEAMID)"
export APPLE_ID="release@atonixcorp.com"
export APPLE_TEAM_ID="TEAMID"
export APPLE_APP_SPECIFIC_PASSWORD="..."
bash dmg/scripts/build_dmg.sh
```

The script creates a native icon, signs the `.app`, signs the DMG, submits it to Apple notarization, staples the notarization ticket, and verifies Gatekeeper acceptance. It fails without signing or notarization credentials.

After installation, launch `AtonixCorp Developer Tools.app` or run its bundled `atonixcorp` binary in a terminal. Use `atonixcorp toolbox sandbox-entity 1` for included toolbox helpers.
