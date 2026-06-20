#!/usr/bin/env python3
"""
Dataset preparation & reconstitution workflow.

``placebot-prep`` filters occurrence/specimen records to those PlaceBot can
usefully georeference (records with locality text and missing or invalid decimal
coordinates) and collapses repeated locality/country targets so each unique
place is georeferenced once. ``placebot-expand`` re-attaches the georeference
results to every original record, making the deduplication lossless.

Both commands work on any locality-bearing dataset — native PlaceBot
(``Barcode`` / ``Locality verbatim`` / ``Country``) files, Darwin Core
downloads, and GBIF occurrence exports — because every column is resolved
through :mod:`placebot.core.field_mapping`.
"""

import argparse
import csv
from pathlib import Path
from typing import Any, Dict, List, Tuple

from placebot.core.deduplication import (
    GEOREFERENCE_COLUMNS,
    TRACKING_COLUMNS,
    dedup_key,
    deduplicate_records,
    filter_records,
    has_valid_decimal_coordinates,
    needs_placebot_georeferencing,
    normalise_dedup_value,
    reconstitute_records,
)
from placebot.core.field_mapping import (
    DWC_OUTPUT_FIELD_MAP,
    get_identifier,
    to_dwc_records,
)

__all__ = [
    "GEOREFERENCE_COLUMNS",
    "dedup_key",
    "deduplicate_records",
    "filter_records",
    "has_valid_decimal_coordinates",
    "needs_placebot_georeferencing",
    "normalise_dedup_value",
    "reconstitute_records",
    "read_records",
    "write_records",
    "run",
    "main",
    "expand_run",
    "expand_main",
]


def detect_delimiter(path: Path) -> str:
    """Detect a simple CSV/TSV delimiter from the header line."""
    first_line = path.read_text(encoding="utf-8-sig").splitlines()[0]
    counts = {
        "\t": first_line.count("\t"),
        ",": first_line.count(","),
        "|": first_line.count("|"),
        ";": first_line.count(";"),
    }
    return max(counts, key=counts.get) if max(counts.values()) > 0 else ","


def read_records(path: Path) -> Tuple[List[Dict[str, Any]], List[str], str]:
    """Read records and return records, header, and delimiter."""
    delimiter = detect_delimiter(path)
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        records = list(reader)
        fieldnames = [name for name in (reader.fieldnames or []) if name is not None]
    return records, fieldnames, delimiter


def write_records(path: Path, records: List[Dict[str, Any]], fieldnames: List[str]) -> None:
    """Write records as CSV or TSV based on the output suffix."""
    delimiter = "\t" if path.suffix.lower() in {".tsv", ".txt"} else ","
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
            delimiter=delimiter,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(records)


def default_output_path(input_path: Path) -> Path:
    """Default output path next to the source file."""
    return input_path.with_name(f"{input_path.stem}_placebot_candidates.tsv")


def run(args: argparse.Namespace) -> int:
    input_path = Path(args.input).expanduser()
    if not input_path.exists():
        print(f"Error: input file not found: {input_path}")
        return 1

    records, fieldnames, _delimiter = read_records(input_path)
    selected, stats = filter_records(
        records,
        include_existing=args.include_existing,
        max_records=args.max_records,
        deduplicate=not args.no_deduplicate,
    )

    output_path = Path(args.output).expanduser() if args.output else default_output_path(input_path)
    output_fieldnames = list(fieldnames)
    if not args.no_deduplicate:
        for field in TRACKING_COLUMNS:
            if field not in output_fieldnames:
                output_fieldnames.append(field)
    write_records(output_path, selected, output_fieldnames)

    print("Preparation complete")
    print(f"Input records: {stats['total']:,}")
    print(f"Records with locality text: {stats['with_locality']:,}")
    print(f"Records with valid decimal coordinates: {stats['with_valid_coordinates']:,}")
    print(f"Records selected before deduplication: {stats['selected']:,}")
    if not args.no_deduplicate:
        print(f"Duplicate locality/country targets removed: {stats['duplicates_removed']:,}")
    print(f"Unique records written for PlaceBot: {len(selected):,}")
    print(f"Output: {output_path}")

    if selected:
        first = selected[0]
        print(f"First selected record: {get_identifier(first)}")

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="placebot-prep",
        description=(
            "Prepare an occurrence/specimen CSV/TSV (native PlaceBot, Darwin "
            "Core, or GBIF) for PlaceBot by selecting records with locality text "
            "and missing/invalid coordinates, collapsing repeated localities."
        ),
    )
    parser.add_argument("input", help="Path to a CSV, TSV, or TXT records file")
    parser.add_argument("-o", "--output", help="Output CSV/TSV path")
    parser.add_argument(
        "--include-existing",
        action="store_true",
        help="Include records even when valid decimal coordinates are present",
    )
    parser.add_argument(
        "--max-records",
        type=int,
        help="Limit the number of selected records written, useful for demos",
    )
    parser.add_argument(
        "--no-deduplicate",
        action="store_true",
        help="Write every selected record instead of one row per locality/country target",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return run(args)


def default_expand_output_path(original_path: Path) -> Path:
    """Default output path for the expanded (reconstituted) file."""
    return original_path.with_name(f"{original_path.stem}_placebot_georeferenced.tsv")


def _dwc_fieldnames(fieldnames: List[str]) -> List[str]:
    """Rename a fieldname list to Darwin Core terms, preserving order."""
    renamed: List[str] = []
    for name in fieldnames:
        target = DWC_OUTPUT_FIELD_MAP.get(name, name)
        if target not in renamed:
            renamed.append(target)
    return renamed


def expand_run(args: argparse.Namespace) -> int:
    original_path = Path(args.original).expanduser()
    processed_path = Path(args.processed).expanduser()
    for path, label in [(original_path, "original"), (processed_path, "processed")]:
        if not path.exists():
            print(f"Error: {label} file not found: {path}")
            return 1

    original_records, original_fieldnames, _ = read_records(original_path)
    processed_records, _, _ = read_records(processed_path)

    expanded, stats = reconstitute_records(original_records, processed_records)

    output_fieldnames = list(original_fieldnames)
    for column in GEOREFERENCE_COLUMNS:
        if column not in output_fieldnames and any(column in row for row in expanded):
            output_fieldnames.append(column)

    records_out = expanded
    if args.dwc:
        records_out = to_dwc_records(expanded)
        output_fieldnames = _dwc_fieldnames(output_fieldnames)

    output_path = (
        Path(args.output).expanduser()
        if args.output
        else default_expand_output_path(original_path)
    )
    write_records(output_path, records_out, output_fieldnames)

    print("Reconstitution complete")
    print(f"Original records: {stats['total']:,}")
    print(f"Records matched to a georeference result: {stats['matched']:,}")
    print(f"Records with no matching result: {stats['unmatched']:,}")
    print(f"Output: {output_path}")

    return 0


def build_expand_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="placebot-expand",
        description=(
            "Reconstitute PlaceBot georeference results back onto every original "
            "record, reversing the deduplication applied by placebot-prep."
        ),
    )
    parser.add_argument(
        "--original",
        required=True,
        help="Path to the full pre-deduplication records CSV/TSV/TXT file",
    )
    parser.add_argument(
        "--processed",
        required=True,
        help="Path to PlaceBot's output for the deduplicated candidate file",
    )
    parser.add_argument("-o", "--output", help="Output CSV/TSV path")
    parser.add_argument(
        "--dwc",
        action="store_true",
        help="Rename produced columns to Darwin Core terms in the output",
    )
    return parser


def expand_main() -> int:
    parser = build_expand_parser()
    args = parser.parse_args()
    return expand_run(args)


if __name__ == "__main__":
    raise SystemExit(main())
