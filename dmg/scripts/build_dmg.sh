#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
VERSION=${VERSION:?Set VERSION for the macOS installer build.}
DIST_DIR="$ROOT_DIR/dmg/dist"
BUILD_DIR="$ROOT_DIR/dmg/build"
VENV_DIR="$BUILD_DIR/venv"
APP_DIR="$BUILD_DIR/AtonixCorp Developer Tools.app"
ICONSET="$BUILD_DIR/AtonixCorp.iconset"

rm -rf "$DIST_DIR" "$BUILD_DIR"
mkdir -p "$DIST_DIR" "$VENV_DIR"
python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/pip" install --upgrade pip pyinstaller
"$VENV_DIR/bin/pip" install "$ROOT_DIR/atonixcorpsdk" "$ROOT_DIR/atonixcorpcli" "$ROOT_DIR/toolbox"

mkdir -p "$ICONSET"
for size in 16 32 128 256 512; do
  sips -s format png -z "$size" "$size" "$ROOT_DIR/app/src/assets/icon-atonixcorp-mark.svg" --out "$ICONSET/icon_${size}x${size}.png"
  doubled=$((size * 2))
  sips -s format png -z "$doubled" "$doubled" "$ROOT_DIR/app/src/assets/icon-atonixcorp-mark.svg" --out "$ICONSET/icon_${size}x${size}@2x.png"
done
iconutil -c icns "$ICONSET" -o "$BUILD_DIR/AtonixCorp.icns"

"$VENV_DIR/bin/pyinstaller" --clean --noconfirm --onefile --name atonixcorp \
  --hidden-import atonixcorp_toolbox.main \
  --add-data "$ROOT_DIR/app/src/assets/icon-atonixcorp-mark.svg:assets" \
  "$ROOT_DIR/dmg/src/desktop_entry.py"

mkdir -p "$APP_DIR/Contents/MacOS" "$APP_DIR/Contents/Resources"
cp "$DIST_DIR/atonixcorp" "$APP_DIR/Contents/MacOS/atonixcorp"
cp "$BUILD_DIR/AtonixCorp.icns" "$APP_DIR/Contents/Resources/AtonixCorp.icns"
cp "$ROOT_DIR/dmg/Info.plist" "$APP_DIR/Contents/Info.plist"
/usr/libexec/PlistBuddy -c "Set :CFBundleShortVersionString $VERSION" "$APP_DIR/Contents/Info.plist"
/usr/libexec/PlistBuddy -c "Set :CFBundleVersion $VERSION" "$APP_DIR/Contents/Info.plist"

if [[ -n "${APPLE_SIGNING_IDENTITY:-}" ]]; then
  codesign --force --options runtime --timestamp --sign "$APPLE_SIGNING_IDENTITY" "$APP_DIR"
else
  echo "Refusing unsigned macOS release build: APPLE_SIGNING_IDENTITY is required." >&2
  exit 1
fi

DMG_PATH="$DIST_DIR/AtonixCorp-Developer-Tools-$VERSION.dmg"
hdiutil create -volname "AtonixCorp Developer Tools" -srcfolder "$APP_DIR" -ov -format UDZO "$DMG_PATH"
codesign --force --timestamp --sign "$APPLE_SIGNING_IDENTITY" "$DMG_PATH"

if [[ -z "${APPLE_ID:-}" || -z "${APPLE_TEAM_ID:-}" || -z "${APPLE_APP_SPECIFIC_PASSWORD:-}" ]]; then
  echo "Refusing unsigned/notarized macOS release build: notarization credentials are required." >&2
  exit 1
fi
xcrun notarytool submit "$DMG_PATH" --apple-id "$APPLE_ID" --team-id "$APPLE_TEAM_ID" --password "$APPLE_APP_SPECIFIC_PASSWORD" --wait
xcrun stapler staple "$DMG_PATH"
spctl -a -vv -t install "$DMG_PATH"
