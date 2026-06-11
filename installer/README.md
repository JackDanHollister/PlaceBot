# Standalone installers

These build double-clickable installers for non-technical users. Each bundles its
own Python runtime and **pip-installs the placebot wheel** (with the `[gui]`
extra) into it — PlaceBot runs as a normal installed package, so there is no
PyInstaller freeze step and no `sys._MEIPASS`/asset-collection fragility.

The GitHub Actions workflow [`.github/workflows/installers.yml`](../.github/workflows/installers.yml)
builds these on `v*` tags and uploads them as workflow artifacts. For stable
version tags without a pre-release suffix (for example `v1.2.5`, not
`v1.2.5-rc1`), the workflow also attaches them to the GitHub Release. You can
trigger it manually ("Run workflow") to dry-run on a branch.

| OS | Output | Tooling |
|----|--------|---------|
| Windows | `dist/PlaceBot-Setup-<ver>.exe` | [Python embeddable package] + [Inno Setup] |
| macOS | `dist/PlaceBot-<ver>.dmg` | [python-build-standalone] + `hdiutil` |

The bundled Python version and the macOS `python-build-standalone` release date
are pinned once in the workflow `env:` block.

**One macOS download for every Mac.** We build an **x86_64** `.dmg`: it runs
natively on Intel and under **Rosetta 2** on Apple Silicon. A true `universal2`
bundle isn't reliable because `pip` installs single-arch wheels for the binary
dependencies (numpy, pandas, pydantic-core, …). CI builds it on the Apple Silicon
runner and runs the x86_64 Python under Rosetta during the `pip` step so the
correct x86_64 wheels are resolved. On Apple Silicon, first launch may prompt a
one-time Rosetta install; runtime overhead is negligible for this API-bound app.

## Build locally

```bash
# 1. Build the wheel both installers consume
python -m build                      # -> dist/placebot-<ver>-py3-none-any.whl

# Windows (PowerShell)
python installer/make_icons.py placebot/gui/placebot_logo.png installer/assets/placebot.ico
./installer/windows/build.ps1 -WheelPath dist\placebot-<ver>-py3-none-any.whl -PythonVersion 3.11.9
iscc /DMyAppVersion=<ver> /DStageDir=$PWD\build\win\PlaceBot /DIconFile=$PWD\installer\assets\placebot.ico installer\windows\placebot.iss

# macOS (x86_64 build; on Apple Silicon, `softwareupdate --install-rosetta` first)
WHEEL_PATH=dist/placebot-<ver>-py3-none-any.whl VERSION=<ver> ARCH=x86_64 \
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
