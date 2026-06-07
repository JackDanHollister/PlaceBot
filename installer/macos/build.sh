#!/bin/bash
#
# Assemble PlaceBot.app and a drag-install .dmg for macOS.
#
# Bundles a relocatable python-build-standalone CPython, pip-installs the
# placebot wheel (with the [gui] extra) into it, wraps it in a .app, and packages
# the result as a .dmg with an /Applications symlink.
#
# We build for ARCH=x86_64 to ship a SINGLE Mac download: an x86_64 bundle runs
# natively on Intel and transparently under Rosetta 2 on Apple Silicon. (A true
# universal2 bundle is not reliable here because pip installs single-arch wheels
# for the binary dependencies - numpy, pandas, pydantic-core, etc.) When built on
# an Apple Silicon CI runner, the x86_64 Python executes under Rosetta during the
# pip step, so pip correctly resolves x86_64 wheels.
#
# Required environment variables:
#   WHEEL_PATH      Path to the built placebot wheel (dist/placebot-*.whl)
#   VERSION         placebot version string (e.g. 1.2.5)
#   ARCH            x86_64 (single-download default) | arm64
#   PYTHON_VERSION  CPython version to embed (e.g. 3.11.9)
#   PBS_DATE        python-build-standalone release date tag (e.g. 20240814)
#
set -euo pipefail

: "${WHEEL_PATH:?set WHEEL_PATH}"
: "${VERSION:?set VERSION}"
: "${ARCH:?set ARCH (arm64|x86_64)}"
: "${PYTHON_VERSION:?set PYTHON_VERSION}"
: "${PBS_DATE:?set PBS_DATE}"

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$HERE/../.." && pwd)"
BUILD="$REPO_ROOT/build/macos-$ARCH"
APP="$BUILD/PlaceBot.app"
RES="$APP/Contents/Resources"
MACOS="$APP/Contents/MacOS"
LOGO="$REPO_ROOT/placebot/gui/placebot_logo.png"

# python-build-standalone uses aarch64 / x86_64 in its asset names.
case "$ARCH" in
  arm64)  PBS_ARCH="aarch64" ;;
  x86_64) PBS_ARCH="x86_64" ;;
  *) echo "Unsupported ARCH: $ARCH" >&2; exit 1 ;;
esac

echo "==> Clean build dir $BUILD"
rm -rf "$BUILD"
mkdir -p "$RES" "$MACOS"

# 1. Download + extract the relocatable Python ("install_only" lays out python/bin/python3).
PBS_FILE="cpython-${PYTHON_VERSION}+${PBS_DATE}-${PBS_ARCH}-apple-darwin-install_only.tar.gz"
PBS_URL="https://github.com/astral-sh/python-build-standalone/releases/download/${PBS_DATE}/${PBS_FILE}"
echo "==> Downloading $PBS_URL"
curl -fL "$PBS_URL" -o "$BUILD/python.tar.gz"
tar -xzf "$BUILD/python.tar.gz" -C "$RES"   # -> $RES/python

PY="$RES/python/bin/python3"

# 2. Install the wheel + [gui] extra. The PEP 508 "name[extra] @ file://" form
#    installs THIS wheel as placebot (pinning the version) and pulls streamlit +
#    runtime deps from PyPI.
WHEEL_ABS="$(cd "$(dirname "$WHEEL_PATH")" && pwd)/$(basename "$WHEEL_PATH")"
echo "==> Installing placebot[gui] from $WHEEL_ABS"
"$PY" -m pip install --upgrade pip
"$PY" -m pip install "placebot[gui] @ file://$WHEEL_ABS"
"$PY" -c "import placebot, streamlit; print('placebot', placebot.__version__, '/ streamlit', streamlit.__version__)"

# 3. App launcher + Info.plist (with version substituted).
cp "$HERE/PlaceBot" "$MACOS/PlaceBot"
chmod +x "$MACOS/PlaceBot"
sed "s/@VERSION@/$VERSION/g" "$HERE/Info.plist" > "$APP/Contents/Info.plist"

# 4. Icon: build a .icns from the logo with native tools.
ICONSET="$BUILD/placebot.iconset"
mkdir -p "$ICONSET"
for sz in 16 32 64 128 256 512; do
  sips -z $sz $sz "$LOGO" --out "$ICONSET/icon_${sz}x${sz}.png" >/dev/null
  dbl=$((sz * 2))
  sips -z $dbl $dbl "$LOGO" --out "$ICONSET/icon_${sz}x${sz}@2x.png" >/dev/null
done
iconutil -c icns "$ICONSET" -o "$RES/placebot.icns"

# 5. Package a drag-install .dmg (PlaceBot.app + Applications symlink).
DMG_STAGE="$BUILD/dmg"
mkdir -p "$DMG_STAGE"
cp -R "$APP" "$DMG_STAGE/"
ln -s /Applications "$DMG_STAGE/Applications"
# Single download for all Macs (x86_64 runs on Intel natively / Apple Silicon
# via Rosetta), so the filename carries no architecture suffix.
DMG_OUT="$REPO_ROOT/dist/PlaceBot-${VERSION}.dmg"
mkdir -p "$REPO_ROOT/dist"
rm -f "$DMG_OUT"
echo "==> Building $DMG_OUT"
hdiutil create -volname "PlaceBot" -srcfolder "$DMG_STAGE" -ov -format UDZO "$DMG_OUT"

echo "==> Done: $DMG_OUT"
