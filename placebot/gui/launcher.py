#!/usr/bin/env python3
"""
PlaceBot GUI Launcher
=====================

Console-script entry point for the Streamlit GUI.

Streamlit apps cannot be started by simply importing and calling a function -
the ``streamlit run`` command needs a script path. We therefore launch
Streamlit's own CLI by rewriting ``sys.argv`` and delegating to
``streamlit.web.cli.main()``. This pattern is stable across Streamlit 1.x,
unlike the lower-level ``bootstrap`` API whose signature has changed between
releases.

The same entry point backs both ``pipx install placebot[gui]`` and the
standalone Windows/macOS installers (which run ``python -m placebot.gui.launcher``
from a bundled Python runtime), so the desktop-friendly touches below -
suppressing Streamlit's first-run e-mail prompt and printing a plain-language
banner - benefit every install path.
"""

import os
import sys
from pathlib import Path


def _suppress_streamlit_first_run_prompt():
    """Avoid Streamlit's interactive "Enter your email" gate on first launch.

    Non-technical users double-clicking a desktop shortcut have no obvious way
    to answer a terminal prompt, so we pre-seed an empty credentials file and
    disable usage-stats gathering. We never overwrite an existing file.
    """
    os.environ.setdefault("STREAMLIT_BROWSER_GATHER_USAGE_STATS", "false")

    creds = Path.home() / ".streamlit" / "credentials.toml"
    if creds.exists():
        return
    try:
        creds.parent.mkdir(parents=True, exist_ok=True)
        creds.write_text('[general]\nemail = ""\n', encoding="utf-8")
    except OSError:
        # A missing credentials file is non-fatal; Streamlit still runs.
        pass


def main():
    """Launch the PlaceBot Streamlit app in the user's browser."""
    try:
        from streamlit.web import cli as stcli
    except ImportError:
        sys.exit(
            "Streamlit is not installed.\n"
            "Install the GUI extra with:\n\n"
            "    pip install 'placebot[gui]'\n"
        )

    _suppress_streamlit_first_run_prompt()

    print(
        "Starting PlaceBot - your web browser will open in a few seconds.\n"
        "Keep this window open while you work; close it to quit PlaceBot.\n",
        flush=True,
    )

    app_path = str(Path(__file__).parent / "app.py")
    sys.argv = [
        "streamlit",
        "run",
        app_path,
        "--browser.gatherUsageStats",
        "false",
    ]
    sys.exit(stcli.main())


if __name__ == "__main__":
    main()
