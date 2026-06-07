# Standalone installers

These build double-clickable installers for non-technical users. Each bundles its
own Python runtime and **pip-installs the placebot wheel** (with the `[gui]`
extra) into it — PlaceBot runs as a normal installed package, so there is no
PyInstaller freeze step and no `sys._MEIPASS`/asset-collection fragility.

The GitHub Actions workflow [`.github/workflows/installers.yml`](../.github/workflows/installers.yml)
builds these on every `v*` tag and attaches them to the GitHub Release. You can
also trigger it manually ("Run workflow") to dry-run on a branch.

| OS | Output | Tooling |
|----|--------|---------|
| Windows | `dist/PlaceBot-Setup-<ver>.exe` | [Python embeddable package] + [Inno Setup] |
| macOS | `dist/PlaceBot-<ver>-<arch>.dmg` | [python-build-standalone] + `hdiutil` |

The bundled Python version and the macOS `python-build-standalone` release date
are pinned once in the workflow `env:` block.

## Build locally

```bash
# 1. Build the wheel both installers consume
python -m build                      # -> dist/placebot-<ver>-py3-none-any.whl

# Windows (PowerShell)
python installer/make_icons.py placebot/gui/placebot_logo.png installer/assets/placebot.ico
./installer/windows/build.ps1 -WheelPath dist\placebot-<ver>-py3-none-any.whl -PythonVersion 3.11.9
iscc /DMyAppVersion=<ver> /DStageDir=$PWD\build\win\PlaceBot /DIconFile=$PWD\installer\assets\placebot.ico installer\windows\placebot.iss

# macOS
WHEEL_PATH=dist/placebot-<ver>-py3-none-any.whl VERSION=<ver> ARCH=arm64 \
  PYTHON_VERSION=3.11.9 PBS_DATE=20240814 bash installer/macos/build.sh
```

## Known gotchas / follow-ups

- **Unsigned builds.** Windows SmartScreen ("More info → Run anyway") and macOS
  Gatekeeper (right-click → Open, or `xattr -dr com.apple.quarantine`) warn on
  first launch. Removing these requires **code signing + notarization**
  (Windows code-signing cert; Apple Developer ID + `notarytool`) — deferred.
- **Antivirus.** Bundled-Python installers are occasionally flagged heuristically;
  signing largely resolves this.
- **Linux.** Not built yet (AppImage / `.desktop` is a future addition).

[Python embeddable package]: https://docs.python.org/3/using/windows.html#the-embeddable-package
[Inno Setup]: https://jrsoftware.org/isinfo.php
[python-build-standalone]: https://github.com/astral-sh/python-build-standalone
