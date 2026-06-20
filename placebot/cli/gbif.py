#!/usr/bin/env python3
"""
GBIF/Darwin Core preparation workflow.

Filters occurrence downloads to records PlaceBot can usefully georeference:
records with locality text and missing or invalid decimal coordinates.
"""

import argparse
import csv
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from placebot.core.coordinate_utils import validate_coordinates
from placebot.core.field_mapping import (
    DWC_OUTPUT_FIELD_MAP,
    get_country,
    get_existing_coordinates,
    get_identifier,
    get_locality,
    to_dwc_records,
)

# Result columns produced by the PlaceBot processor (see
# placebot/core/batch_processor.py). These are copied from a deduplicated,
# georeferenced result back onto every original occurrence during expansion.
GEOREFERENCE_COLUMNS = [
    "Country_Processed",
    "State",
    "Region",
    "Sector",
    "Exact_Site",
    "Latitude",
    "Longitude",
    "Coordinate_Source",
    "Coordinate_Radius_Meters",
    "Elevation",
    "Elevation_Original",
    "Confidence",
    "Processing_Notes",
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
    """Read occurrence records and return records, header, and delimiter."""
    delimiter = detect_delimiter(path)
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        records = list(reader)
        fieldnames = [name for name in (reader.fieldnames or []) if name is not None]
    return records, fieldnames, delimiter


def has_valid_decimal_coordinates(record: Dict[str, Any]) -> bool:
    """True if the record has valid decimal latitude and longitude."""
    lat, lon = get_existing_coordinates(record)
    parsed_lat, parsed_lon = validate_coordinates(lat, lon)
    return parsed_lat is not None and parsed_lon is not None


def needs_placebot_georeferencing(
    record: Dict[str, Any],
    include_existing: bool = False,
) -> bool:
    """True if this record should be included in the PlaceBot prep file."""
    locality = get_locality(record)
    if not locality:
        return False
    if include_existing:
        return True
    return not has_valid_decimal_coordinates(record)


def normalise_dedup_value(value: Any) -> str:
    """Normalise text used in deduplication keys."""
    return " ".join(str(value or "").strip().lower().split())


def dedup_key(record: Dict[str, Any]) -> str:
    """Georeferencing target key: locality plus country context."""
    locality = normalise_dedup_value(get_locality(record))
    country = normalise_dedup_value(get_country(record))
    return f"{locality}|{country}"


def deduplicate_records(records: Iterable[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], int]:
    """Collapse repeated locality/country targets while keeping occurrence IDs."""
    grouped: Dict[str, Dict[str, Any]] = {}
    duplicate_count = 0

    for record in records:
        key = dedup_key(record)
        occurrence_id = get_identifier(record, default="")
        if key not in grouped:
            grouped_record = dict(record)
            grouped_record["placebotDedupKey"] = key
            grouped_record["placebotOccurrenceIDs"] = occurrence_id
            grouped_record["placebotOccurrenceCount"] = "1"
            grouped[key] = grouped_record
            continue

        duplicate_count += 1
        grouped_record = grouped[key]
        ids = [
            value for value in grouped_record.get("placebotOccurrenceIDs", "").split("|")
            if value
        ]
        if occurrence_id and occurrence_id not in ids:
            ids.append(occurrence_id)
            grouped_record["placebotOccurrenceIDs"] = "|".join(ids)
        grouped_record["placebotOccurrenceCount"] = str(
            int(grouped_record.get("placebotOccurrenceCount") or "1") + 1
        )

    return list(grouped.values()), duplicate_count


def reconstitute_records(
    original_records: Iterable[Dict[str, Any]],
    processed_records: Iterable[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    """Re-expand deduplicated georeference results back to every occurrence.

    ``original_records`` is the full pre-deduplication occurrence file;
    ``processed_records`` is PlaceBot's output for the deduplicated candidates.
    Records are joined on :func:`dedup_key` (locality + country), which is the
    same deterministic key used to collapse them, so it does not depend on the
    ``placebotOccurrenceIDs`` tracking column surviving processing.

    Returns the expanded records (one per original occurrence) plus counts.
    """
    results_by_key: Dict[str, Dict[str, Any]] = {}
    for result in processed_records:
        results_by_key[dedup_key(result)] = result

    expanded: List[Dict[str, Any]] = []
    stats = {"total": 0, "matched": 0, "unmatched": 0}

    for record in original_records:
        stats["total"] += 1
        row = dict(record)
        result = results_by_key.get(dedup_key(record))
        if result is None:
            stats["unmatched"] += 1
        else:
            stats["matched"] += 1
            for column in GEOREFERENCE_COLUMNS:
                if column in result:
                    row[column] = result[column]
        expanded.append(row)

    return expanded, stats


def filter_records(
    records: Iterable[Dict[str, Any]],
    include_existing: bool = False,
    max_records: Optional[int] = None,
    deduplicate: bool = True,
) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    """Filter occurrence records and return selected records plus counts."""
    candidates: List[Dict[str, Any]] = []
    stats = {
        "total": 0,
        "with_locality": 0,
        "with_valid_coordinates": 0,
        "selected": 0,
        "duplicates_removed": 0,
    }

    for record in records:
        stats["total"] += 1
        if get_locality(record):
            stats["with_locality"] += 1
        if has_valid_decimal_coordinates(record):
            stats["with_valid_coordinates"] += 1

        selected_is_full = max_records is not None and len(candidates) >= max_records
        if (
            not selected_is_full
            and needs_placebot_georeferencing(record, include_existing=include_existing)
        ):
            candidates.append(record)
            stats["selected"] += 1

    if deduplicate:
        selected, duplicate_count = deduplicate_records(candidates)
        stats["duplicates_removed"] = duplicate_count
    else:
        selected = candidates

    return selected, stats


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
        for field in ["placebotDedupKey", "placebotOccurrenceIDs", "placebotOccurrenceCount"]:
            if field not in output_fieldnames:
                output_fieldnames.append(field)
    write_records(output_path, selected, output_fieldnames)

    print("GBIF/Darwin Core preparation complete")
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
        prog="placebot-gbif-prep",
        description=(
            "Prepare a GBIF/Darwin Core occurrence CSV/TSV for PlaceBot by "
            "selecting records with locality text and missing/invalid coordinates."
        ),
    )
    parser.add_argument("input", help="Path to a GBIF/Darwin Core CSV, TSV, or TXT file")
    parser.add_argument("-o", "--output", help="Output CSV/TSV path")
    parser.add_argument(
        "--include-existing",
        action="store_true",
        help="Include records even when valid decimalLatitude/decimalLongitude are present",
    )
    parser.add_argument(
        "--max-records",
        type=int,
        help="Limit the number of selected records written, useful for demos",
    )
    parser.add_argument(
        "--no-deduplicate",
        action="store_true",
        help="Write every selected occurrence instead of one row per locality/country target",
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

    print("GBIF/Darwin Core reconstitution complete")
    print(f"Original occurrences: {stats['total']:,}")
    print(f"Occurrences matched to a georeference result: {stats['matched']:,}")
    print(f"Occurrences with no matching result: {stats['unmatched']:,}")
    print(f"Output: {output_path}")

    return 0


def build_expand_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="placebot-gbif-expand",
        description=(
            "Reconstitute PlaceBot georeference results back onto every original "
            "GBIF/Darwin Core occurrence, reversing the deduplication applied by "
            "placebot-gbif-prep."
        ),
    )
    parser.add_argument(
        "--original",
        required=True,
        help="Path to the full pre-deduplication occurrence CSV/TSV/TXT file",
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
