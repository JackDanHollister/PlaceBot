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
"""

import sys
from pathlib import Path


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
