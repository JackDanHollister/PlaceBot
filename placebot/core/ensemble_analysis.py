#!/usr/bin/env python3
"""
Ensemble Analysis
=================

Compare the coordinate estimates from two PlaceBot runs (typically the same
dataset processed by two different LLMs) and flag records for manual
verification based on how far apart the two estimates are.

Records are merged on their ``Barcode``. For each record the great-circle
(haversine) distance between the two models' coordinates is computed and bucketed
into an agreement category:

    close (<2km)  ·  moderate (2-5km)  ·  low (5-10km)  ·  none (>10km)

Records where either coordinate is missing/invalid, or whose barcode only
appears in one file, fall into "no comparison".

The "primary" file's values are carried forward into the output; the secondary
file only contributes its coordinates (for reference) and the distance/category.

Both the CLI (``placebot-ensemble``) and the GUI call :func:`run_ensemble`.
"""

import csv
import json
import os
from collections import OrderedDict
from typing import Any, Dict, List, Optional

import numpy as np

from placebot.core.coordinate_utils import validate_coordinates


# ---------------------------------------------------------------------------
# Agreement categories
# ---------------------------------------------------------------------------

CATEGORY_CLOSE = "close (<2km)"
CATEGORY_MODERATE = "moderate (2-5km)"
CATEGORY_LOW = "low (5-10km)"
CATEGORY_NONE = "none (>10km)"
CATEGORY_NO_COMPARISON = "no comparison"

# Ordered so summaries always list every bucket (including zero counts).
CATEGORIES = [
    CATEGORY_CLOSE,
    CATEGORY_MODERATE,
    CATEGORY_LOW,
    CATEGORY_NONE,
    CATEGORY_NO_COMPARISON,
]

# Columns appended to each carried-forward record.
AGREEMENT_COLUMN = "Agreement_Category"
DISTANCE_COLUMN = "Distance_km"
SECONDARY_LAT_COLUMN = "Secondary_Latitude"
SECONDARY_LON_COLUMN = "Secondary_Longitude"


# ---------------------------------------------------------------------------
# Haversine
# ---------------------------------------------------------------------------

def haversine_distance(lat1, lon1, lat2, lon2):
    """Great-circle distance in km between two points (decimal degrees).

    Works on scalars or array-likes. Mirrors the reference implementation in
    ``compare_model_coordinates.py``.
    """
    R = 6371.0  # Earth radius in km
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    return R * 2 * np.arcsin(np.sqrt(a))


def categorise(distance_km: Optional[float]) -> str:
    """Map a distance in km to an agreement category."""
    if distance_km is None:
        return CATEGORY_NO_COMPARISON
    if distance_km < 2:
        return CATEGORY_CLOSE
    if distance_km < 5:
        return CATEGORY_MODERATE
    if distance_km < 10:
        return CATEGORY_LOW
    return CATEGORY_NONE


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def _detect_delimiter(first_line: str) -> str:
    """Return the most common of tab/comma/pipe/semicolon, defaulting to comma."""
    counts = {
        "\t": first_line.count("\t"),
        ",": first_line.count(","),
        "|": first_line.count("|"),
        ";": first_line.count(";"),
    }
    best = max(counts, key=counts.get)
    return best if counts[best] > 0 else ","


def load_records(path: str) -> List[Dict[str, Any]]:
    """Load records from a PlaceBot output file (CSV/TSV/TXT or JSON).

    JSON may be a top-level list, or a dict wrapping the records under
    ``records``/``data``, or a GeoJSON FeatureCollection (properties are
    extracted and the geometry's coordinates folded back into
    Latitude/Longitude).
    """
    ext = os.path.splitext(path)[1].lower()

    if ext in (".json", ".geojson"):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return _records_from_json(data)

    # Delimited text. utf-8-sig transparently strips a BOM if present.
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        first_line = f.readline()
        if not first_line.strip():
            return []
        delimiter = _detect_delimiter(first_line)
        f.seek(0)
        reader = csv.DictReader(f, delimiter=delimiter)
        return [dict(row) for row in reader]


def _records_from_json(data: Any) -> List[Dict[str, Any]]:
    """Normalise a parsed JSON payload into a list of record dicts."""
    if isinstance(data, list):
        return [r for r in data if isinstance(r, dict)]

    if isinstance(data, dict):
        # GeoJSON FeatureCollection
        if data.get("type") == "FeatureCollection" and isinstance(data.get("features"), list):
            records = []
            for feat in data["features"]:
                if not isinstance(feat, dict):
                    continue
                props = dict(feat.get("properties") or {})
                geom = feat.get("geometry") or {}
                coords = geom.get("coordinates")
                if isinstance(coords, (list, tuple)) and len(coords) >= 2:
                    # GeoJSON is [lon, lat]
                    props.setdefault("Longitude", coords[0])
                    props.setdefault("Latitude", coords[1])
                records.append(props)
            return records
        # Wrapped list
        for key in ("records", "data", "results"):
            if isinstance(data.get(key), list):
                return [r for r in data[key] if isinstance(r, dict)]

    return []


# ---------------------------------------------------------------------------
# Case-tolerant field access
# ---------------------------------------------------------------------------

def _get(record: Dict[str, Any], *names: str) -> Any:
    """Return the first present value among ``names`` (case-insensitive fallback)."""
    for name in names:
        if name in record and record[name] not in (None, ""):
            return record[name]
    lowered = {str(k).lower(): v for k, v in record.items()}
    for name in names:
        val = lowered.get(name.lower())
        if val not in (None, ""):
            return val
    return None


def _barcode(record: Dict[str, Any]) -> Optional[str]:
    bc = _get(record, "Barcode", "barcode", "locality_id", "id")
    return str(bc).strip() if bc not in (None, "") else None


def _coords(record: Dict[str, Any]):
    lat = _get(record, "Latitude", "latitude", "lat")
    lon = _get(record, "Longitude", "longitude", "lon", "long")
    return validate_coordinates(lat, lon)


# ---------------------------------------------------------------------------
# Core comparison
# ---------------------------------------------------------------------------

def run_ensemble(primary_path: str, secondary_path: str) -> Dict[str, Any]:
    """Compare two PlaceBot output files and build annotated output records.

    Returns a dict with:
        records           - carried-forward primary records + agreement columns
        summary           - OrderedDict[category -> count]
        primary_name      - basename of the primary file
        secondary_name    - basename of the secondary file
        total             - number of output records (= primary record count)
        only_in_primary   - barcodes present only in the primary file
        only_in_secondary - barcodes present only in the secondary file
        duplicate_barcodes- duplicate barcodes seen in the secondary file
    """
    primary = load_records(primary_path)
    secondary = load_records(secondary_path)

    # Index secondary by barcode (keep first occurrence; count duplicates).
    secondary_index: Dict[str, Dict[str, Any]] = {}
    duplicate_barcodes = 0
    for rec in secondary:
        bc = _barcode(rec)
        if bc is None:
            continue
        if bc in secondary_index:
            duplicate_barcodes += 1
            continue
        secondary_index[bc] = rec

    matched_secondary = set()
    output_records: List[Dict[str, Any]] = []
    only_in_primary = 0

    for rec in primary:
        out = dict(rec)  # carry forward all primary columns
        bc = _barcode(rec)
        sec = secondary_index.get(bc) if bc is not None else None

        distance = None
        sec_lat = sec_lon = None
        if sec is not None:
            matched_secondary.add(bc)
            lat1, lon1 = _coords(rec)
            sec_lat, sec_lon = _coords(sec)
            if None not in (lat1, lon1, sec_lat, sec_lon):
                distance = round(float(haversine_distance(lat1, lon1, sec_lat, sec_lon)), 3)
        else:
            only_in_primary += 1

        out[AGREEMENT_COLUMN] = categorise(distance)
        out[DISTANCE_COLUMN] = distance if distance is not None else ""
        out[SECONDARY_LAT_COLUMN] = sec_lat if sec_lat is not None else ""
        out[SECONDARY_LON_COLUMN] = sec_lon if sec_lon is not None else ""
        output_records.append(out)

    only_in_secondary = sum(
        1 for bc in secondary_index if bc not in matched_secondary
    )

    return {
        "records": output_records,
        "summary": summarise(output_records),
        "primary_name": os.path.basename(primary_path),
        "secondary_name": os.path.basename(secondary_path),
        "total": len(output_records),
        "only_in_primary": only_in_primary,
        "only_in_secondary": only_in_secondary,
        "duplicate_barcodes": duplicate_barcodes,
    }


def summarise(records: List[Dict[str, Any]]) -> "OrderedDict[str, int]":
    """Count records per agreement category (every category present, incl. zero)."""
    counts: "OrderedDict[str, int]" = OrderedDict((cat, 0) for cat in CATEGORIES)
    for rec in records:
        cat = rec.get(AGREEMENT_COLUMN, CATEGORY_NO_COMPARISON)
        if cat in counts:
            counts[cat] += 1
        else:
            counts[CATEGORY_NO_COMPARISON] += 1
    return counts
