# Brandinyx Social Assets

This folder contains square social-media-ready logo exports for Ledgora.

These files are generated from the current platform icon so the social avatar stays identical to the existing product icon.

Files:
- `logo-icon-social.svg`: copy of the current platform icon artwork.
- `generate_social_pngs.py`: regenerates the PNG exports by rasterizing `logo-icon-social.svg` directly.
- `logo-icon-social-512.png`: standard avatar/icon export.
- `logo-icon-social-1024.png`: high-resolution avatar/icon export.
- `logo-icon-social-1200.png`: social post/profile export.

Regenerate:

```bash
/Users/ofidohubvm/Ledgora/api/.venv/bin/python brandinyx/generate_social_pngs.py
```