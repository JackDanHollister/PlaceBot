#!/usr/bin/env python3
"""
Generate platform icons from the bundled PlaceBot logo.

Produces a multi-resolution Windows ``.ico`` from ``placebot/gui/placebot_logo.png``.
(macOS ``.icns`` is generated separately in ``installer/macos/build.sh`` using the
native ``sips``/``iconutil`` tools, which are only available on macOS.)

Usage:
    python installer/make_icons.py <source_png> <output_ico>

Requires Pillow (installed on the build runner, not in the shipped runtime).
"""

import sys
from pathlib import Path

from PIL import Image

# Standard Windows icon sizes; Explorer/shortcuts pick the best fit.
ICO_SIZES = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]


def main():
    if len(sys.argv) != 3:
        sys.exit("usage: make_icons.py <source_png> <output_ico>")

    src = Path(sys.argv[1])
    out = Path(sys.argv[2])
    out.parent.mkdir(parents=True, exist_ok=True)

    img = Image.open(src).convert("RGBA")
    img.save(out, format="ICO", sizes=ICO_SIZES)
    print(f"Wrote {out} ({', '.join(f'{w}x{h}' for w, h in ICO_SIZES)})")


if __name__ == "__main__":
    main()
