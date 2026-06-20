#!/usr/bin/env python3
"""
Locality deduplication & reconstitution
=======================================

Dataset-agnostic helpers for collapsing repeated georeferencing targets before
processing and re-expanding the results afterwards.

These functions read every input column through :mod:`placebot.core.field_mapping`
(``get_locality`` / ``get_country`` / ``get_identifier`` /
``get_existing_coordinates``), which already resolves native PlaceBot column
names, Darwin Core terms, and GBIF occurrence columns alike. Nothing here is
specific to GBIF: any locality-bearing dataset (native ``Locality verbatim`` /
``Country`` / ``Barcode`` files, Darwin Core downloads, GBIF exports) flows
through the same single code path.

The workflow is two halves:

* **deduplicate** repeated locality/country targets so each unique place is
  georeferenced once (cost saving), tracking the original record identifiers; then
* **reconstitute** the georeference results back onto every original record so
  the deduplication is lossless.
"""

from typing import Any, Dict, Iterable, List, Optional, Tuple

from placebot.core.coordinate_utils import validate_coordinates
from placebot.core.field_mapping import (
    get_country,
    get_existing_coordinates,
    get_identifier,
    get_locality,
)

# Tracking columns added to a deduplicated record so the collapse can be audited
# and reversed. Written by ``deduplicate_records`` and consumed (optionally) by
# downstream tooling.
DEDUP_KEY_COLUMN = "placebotDedupKey"
OCCURRENCE_IDS_COLUMN = "placebotOccurrenceIDs"
OCCURRENCE_COUNT_COLUMN = "placebotOccurrenceCount"
TRACKING_COLUMNS = [DEDUP_KEY_COLUMN, OCCURRENCE_IDS_COLUMN, OCCURRENCE_COUNT_COLUMN]

# Result columns produced by the PlaceBot processor (see
# placebot/core/batch_processor.py). These are copied from a deduplicated,
# georeferenced result back onto every original record during reconstitution.
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
            grouped_record[DEDUP_KEY_COLUMN] = key
            grouped_record[OCCURRENCE_IDS_COLUMN] = occurrence_id
            grouped_record[OCCURRENCE_COUNT_COLUMN] = "1"
            grouped[key] = grouped_record
            continue

        duplicate_count += 1
        grouped_record = grouped[key]
        ids = [
            value for value in grouped_record.get(OCCURRENCE_IDS_COLUMN, "").split("|")
            if value
        ]
        if occurrence_id and occurrence_id not in ids:
            ids.append(occurrence_id)
            grouped_record[OCCURRENCE_IDS_COLUMN] = "|".join(ids)
        grouped_record[OCCURRENCE_COUNT_COLUMN] = str(
            int(grouped_record.get(OCCURRENCE_COUNT_COLUMN) or "1") + 1
        )

    return list(grouped.values()), duplicate_count


def reconstitute_records(
    original_records: Iterable[Dict[str, Any]],
    processed_records: Iterable[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    """Re-expand deduplicated georeference results back to every record.

    ``original_records`` is the full pre-deduplication file;
    ``processed_records`` is PlaceBot's output for the deduplicated candidates.
    Records are joined on :func:`dedup_key` (locality + country), which is the
    same deterministic key used to collapse them, so it does not depend on the
    ``placebotOccurrenceIDs`` tracking column surviving processing.

    Returns the expanded records (one per original record) plus counts.
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
    """Filter records to those PlaceBot can usefully georeference, plus counts."""
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
