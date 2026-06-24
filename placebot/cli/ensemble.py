#!/usr/bin/env python3
"""
PlaceBot Ensemble Analysis (CLI)
================================

Compare two PlaceBot output files (typically the same dataset processed by two
different LLMs) and flag records for manual verification.

Usage:
    placebot-ensemble                         # interactive file picker
    placebot-ensemble PRIMARY SECONDARY       # non-interactive (TSV + CSV out)

The PRIMARY file's values are carried forward; the output gains an agreement
category and the distance (km) between the two estimates, so records can be
filtered for manual checking. A summary report of the per-category counts is
printed at the end.
"""

import os
import sys

from placebot.core.data_dirs import get_output_dir, setup_directories
from placebot.core.ensemble_analysis import CATEGORIES, run_ensemble
from placebot.core.output_formatter import OutputFormatter

# Files in the output folder that are not comparison candidates.
_SKIP_SUFFIXES = ("_progress.tsv",)
_SKIP_NAMES = ("readme.txt",)
_VALID_EXTS = (".csv", ".tsv", ".txt", ".json")


def _discover_output_files():
    """Return candidate output files under the output dir (newest first)."""
    out_dir = str(get_output_dir())
    found = []
    for root, _dirs, files in os.walk(out_dir):
        for name in files:
            lower = name.lower()
            if not lower.endswith(_VALID_EXTS):
                continue
            if lower in _SKIP_NAMES or lower.endswith(_SKIP_SUFFIXES):
                continue
            # Skip GeoJSON (no merge value) and batch-job metadata.
            if lower.endswith(".geojson") or "batch_jobs" in root:
                continue
            path = os.path.join(root, name)
            try:
                if os.path.getsize(path) == 0:
                    continue
                mtime = os.path.getmtime(path)
            except OSError:
                continue
            found.append((path, mtime))
    found.sort(key=lambda t: t[1], reverse=True)
    return [p for p, _ in found]


def _display_path(path):
    """Show the path relative to the output dir for a tidy listing."""
    out_dir = str(get_output_dir())
    try:
        return os.path.relpath(path, out_dir)
    except ValueError:
        return path


def _prompt_index(prompt, count, exclude=None):
    """Prompt for a 1-based index in [1, count], optionally excluding one."""
    while True:
        raw = input(prompt).strip()
        if not raw:
            return None
        try:
            idx = int(raw) - 1
        except ValueError:
            print("   Please enter a number.")
            continue
        if idx < 0 or idx >= count:
            print(f"   Please enter a number between 1 and {count}.")
            continue
        if exclude is not None and idx == exclude:
            print("   That's the same file — pick a different one.")
            continue
        return idx


def _prompt_formats():
    """Ask which output formats to write (defaults to TSV + CSV)."""
    raw = input(
        "\nOutput formats [tsv,csv,json,geojson] (Enter for tsv,csv): "
    ).strip().lower()
    if not raw:
        return ["tsv", "csv"]
    formats = [f.strip() for f in raw.replace(" ", ",").split(",") if f.strip()]
    valid = {"tsv", "csv", "json", "geojson"}
    formats = [f for f in formats if f in valid]
    return formats or ["tsv", "csv"]


def _print_summary(result):
    """Print the per-category counts and merge stats."""
    total = result["total"]
    print("\n" + "=" * 70)
    print("ENSEMBLE SUMMARY")
    print("=" * 70)
    print(f"Primary   : {result['primary_name']}  (values carried forward)")
    print(f"Secondary : {result['secondary_name']}")
    print(f"Records   : {total:,}")
    print("-" * 70)
    for cat in CATEGORIES:
        count = result["summary"].get(cat, 0)
        pct = (count / total * 100) if total else 0
        print(f"  {cat:<20} {count:>8,}  ({pct:5.1f}%)")
    print("-" * 70)
    if result["only_in_primary"]:
        print(f"  Barcodes only in primary  : {result['only_in_primary']:,}")
    if result["only_in_secondary"]:
        print(f"  Barcodes only in secondary: {result['only_in_secondary']:,}")
    if result["duplicate_barcodes"]:
        print(f"  Duplicate barcodes in secondary (ignored): "
              f"{result['duplicate_barcodes']:,}")
    print("=" * 70)


def _analyse(primary, secondary, formats):
    """Run the comparison, write outputs, and print the summary."""
    print(f"\nComparing:\n  primary   = {primary}\n  secondary = {secondary}")
    result = run_ensemble(primary, secondary)

    if not result["records"]:
        print("\n⚠️  No records to compare (empty or unreadable files).")
        return 1

    prim_stem = os.path.splitext(os.path.basename(primary))[0]
    sec_stem = os.path.splitext(os.path.basename(secondary))[0]
    base = os.path.join(str(get_output_dir()), f"ensemble_{prim_stem}_vs_{sec_stem}")
    saved = OutputFormatter.write_output(
        result["records"], base, formats, fieldnames=result.get("fieldnames")
    )

    _print_summary(result)
    print("\nSaved:")
    for fmt, path in saved.items():
        print(f"   {fmt.upper():<8} {path}")
    return 0


def _interactive():
    files = _discover_output_files()
    if len(files) < 2:
        print(
            "\nNeed at least two output files to compare.\n"
            f"Looked in: {get_output_dir()}\n"
            "Run two models on the same dataset first (results land in your "
            "output folder)."
        )
        return 1

    print("\nAvailable output files:")
    for i, path in enumerate(files, 1):
        size_kb = os.path.getsize(path) / 1024
        print(f"  {i:>3}. {_display_path(path)}  ({size_kb:,.0f} KB)")

    primary_idx = _prompt_index(
        "\nSelect the PRIMARY file (values carried forward) [number]: ",
        len(files),
    )
    if primary_idx is None:
        print("Cancelled.")
        return 1

    secondary_idx = _prompt_index(
        "Select the SECONDARY file [number]: ",
        len(files),
        exclude=primary_idx,
    )
    if secondary_idx is None:
        print("Cancelled.")
        return 1

    formats = _prompt_formats()
    return _analyse(files[primary_idx], files[secondary_idx], formats)


def main():
    setup_directories()

    print("=" * 70)
    print("PLACEBOT ENSEMBLE ANALYSIS")
    print("=" * 70)

    # Non-interactive: placebot-ensemble PRIMARY SECONDARY
    if len(sys.argv) >= 3:
        primary, secondary = sys.argv[1], sys.argv[2]
        for path in (primary, secondary):
            if not os.path.exists(path):
                print(f"Error: file not found: {path}")
                return 1
        return _analyse(primary, secondary, ["tsv", "csv"])

    if len(sys.argv) == 2:
        print(__doc__)
        return 1

    try:
        return _interactive()
    except (KeyboardInterrupt, EOFError):
        print("\nCancelled.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
