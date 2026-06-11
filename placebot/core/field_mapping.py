#!/usr/bin/env python3
"""
Field Mapping (Darwin Core aware)
=================================

Centralises how PlaceBot reads input columns and (optionally) renames output
columns to Darwin Core (DwC) terms.

Why this exists
---------------
PlaceBot historically looked for a small set of hard-coded column names
("Locality verbatim", "Country", "Barcode", "Latitude"/"Longitude"). Natural
history data is very commonly published using Darwin Core terms
(https://dwc.tdwg.org/terms/), so a file with ``verbatimLocality`` / ``country``
/ ``collectionID`` columns would previously have been ignored.

Input resolution here recognises DwC terms as aliases for the concepts PlaceBot
needs, so a DwC-formatted file "just works" with no manual column mapping. The
original names are kept first in each alias list so existing files behave
exactly as before.

Output mapping is opt-in: when DwC output is requested, the columns PlaceBot
*produces* are renamed to their closest DwC equivalents. The internal/working
files (progress + resume TSVs) always keep the native names so resume logic is
unaffected; only the final user-facing exports are renamed.
"""

from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Input resolution
# ---------------------------------------------------------------------------

# For each concept, the column names PlaceBot will accept, in priority order.
# Native PlaceBot names come first so existing datasets are unaffected; Darwin
# Core terms follow.
LOCALITY_FIELDS = ("Locality verbatim", "label_verbatim", "verbatimLocality", "locality")
COUNTRY_FIELDS = ("Country", "country")
IDENTIFIER_FIELDS = (
    "Barcode",
    "catalogNumber",
    "occurrenceID",
    "collectionID",
    "materialEntityID",
    "recordNumber",
)
# Decimal (numeric) coordinates - fed to the existing "preserve these exact
# coordinates" path after validation.
DECIMAL_LAT_FIELDS = ("Latitude", "latitude", "decimalLatitude")
DECIMAL_LON_FIELDS = ("Longitude", "longitude", "decimalLongitude")
# Verbatim (free-text) coordinates - e.g. DMS strings the AI can interpret but
# that won't pass numeric validation. Surfaced to the model as extra context.
VERBATIM_LAT_FIELDS = ("verbatimLatitude",)
VERBATIM_LON_FIELDS = ("verbatimLongitude",)
VERBATIM_COORD_FIELDS = ("verbatimCoordinates",)


def _first_nonempty(record: Dict[str, Any], fields) -> Optional[Any]:
    """Return the first present, non-empty value among ``fields`` (in order)."""
    for field in fields:
        if field in record:
            value = record.get(field)
            if value is not None and str(value).strip() != "":
                return value
    return None


def get_country(record: Dict[str, Any], default: str = "") -> str:
    """Resolve the country for a record from native or DwC columns."""
    value = _first_nonempty(record, COUNTRY_FIELDS)
    return str(value).strip() if value is not None else default


def get_identifier(record: Dict[str, Any], default: str = "Unknown") -> str:
    """Resolve a record identifier (barcode / catalogNumber / occurrenceID...)."""
    value = _first_nonempty(record, IDENTIFIER_FIELDS)
    return str(value).strip() if value is not None else default


def get_existing_coordinates(record: Dict[str, Any]) -> Tuple[Any, Any]:
    """Return raw (latitude, longitude) from decimal columns, or ('', '').

    Values are returned unparsed; callers validate them via
    ``coordinate_utils.validate_coordinates``.
    """
    lat = _first_nonempty(record, DECIMAL_LAT_FIELDS)
    lon = _first_nonempty(record, DECIMAL_LON_FIELDS)
    return (lat if lat is not None else "", lon if lon is not None else "")


def _verbatim_coordinate_text(record: Dict[str, Any]) -> str:
    """Combine any verbatim coordinate columns into a single hint string."""
    parts = []
    combined = _first_nonempty(record, VERBATIM_COORD_FIELDS)
    if combined:
        parts.append(str(combined).strip())
    vlat = _first_nonempty(record, VERBATIM_LAT_FIELDS)
    vlon = _first_nonempty(record, VERBATIM_LON_FIELDS)
    if vlat and vlon:
        parts.append(f"{str(vlat).strip()} {str(vlon).strip()}")
    return "; ".join(parts)


def get_locality(record: Dict[str, Any], default: str = "") -> str:
    """Resolve the verbatim locality text from native or DwC columns."""
    value = _first_nonempty(record, LOCALITY_FIELDS)
    return str(value).strip() if value is not None else default


def get_ai_locality(record: Dict[str, Any], default: str = "") -> str:
    """Locality text to send to the AI.

    Same as :func:`get_locality`, but when the record carries only *verbatim*
    (non-numeric) coordinates - e.g. DwC ``verbatimCoordinates`` or
    ``verbatimLatitude``/``verbatimLongitude`` in DMS - and no parseable decimal
    coordinates, those are appended as a hint so the model can still use them.
    """
    locality = get_locality(record, default=default)
    lat, lon = get_existing_coordinates(record)
    has_decimal = str(lat).strip() != "" and str(lon).strip() != ""
    if not has_decimal:
        verbatim = _verbatim_coordinate_text(record)
        if verbatim:
            hint = f"[verbatim coordinates: {verbatim}]"
            locality = f"{locality} {hint}".strip() if locality else hint
    return locality


# ---------------------------------------------------------------------------
# Input detection (used for dataset previews / "has locality" hints)
# ---------------------------------------------------------------------------

def has_locality_column(columns) -> bool:
    """True if any column looks like a locality/location text field (incl. DwC)."""
    lowered = [str(c).lower() for c in columns]
    if any(c in {f.lower() for f in LOCALITY_FIELDS} for c in lowered):
        return True
    return any("locality" in c or "location" in c for c in lowered)


def has_identifier_column(columns) -> bool:
    """True if any column looks like a record identifier (incl. DwC terms)."""
    lowered = [str(c).lower() for c in columns]
    known = {f.lower() for f in IDENTIFIER_FIELDS}
    if any(c in known for c in lowered):
        return True
    return any("barcode" in c or c == "id" or c.endswith("id") for c in lowered)


# ---------------------------------------------------------------------------
# Output mapping (opt-in Darwin Core export)
# ---------------------------------------------------------------------------

# PlaceBot's produced/passthrough columns -> closest Darwin Core term. Where two
# source columns map to the same DwC term (e.g. the raw input Country and the
# AI-resolved Country_Processed both -> ``country``), the later, non-empty value
# wins (see :func:`to_dwc_record`).
DWC_OUTPUT_FIELD_MAP = {
    "Barcode": "catalogNumber",
    "Locality verbatim": "verbatimLocality",
    "Country": "country",
    "Country_Processed": "country",
    "State": "stateProvince",
    "Region": "county",
    "Sector": "municipality",
    "Exact_Site": "locality",
    "Elevation": "minimumElevationInMeters",
    "Elevation_Original": "verbatimElevation",
    "Latitude": "decimalLatitude",
    "Longitude": "decimalLongitude",
    "Coordinate_Radius_Meters": "coordinateUncertaintyInMeters",
    "Coordinate_Source": "georeferenceProtocol",
    "Confidence": "georeferenceVerificationStatus",
    "Processing_Notes": "georeferenceRemarks",
}

# Canonical column order for DwC exports (native order mapped through the table,
# de-duplicated, preserving first occurrence).
_DWC_NATIVE_ORDER = [
    "Barcode", "Locality verbatim", "Country", "Country_Processed",
    "State", "Region", "Sector", "Exact_Site", "Elevation",
    "Elevation_Original", "Latitude", "Longitude",
    "Coordinate_Radius_Meters", "Coordinate_Source",
    "Confidence", "Processing_Notes",
]


def _dedupe(seq: List[str]) -> List[str]:
    seen = set()
    out = []
    for item in seq:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


DWC_COLUMN_ORDER = _dedupe(
    [DWC_OUTPUT_FIELD_MAP.get(col, col) for col in _DWC_NATIVE_ORDER]
)


def to_dwc_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """Rename a single record's keys to Darwin Core terms.

    Columns without a mapping are passed through unchanged. When two source
    columns collapse to the same DwC term, a non-empty value never overwrites
    with an empty one, and a later non-empty value (e.g. the AI-resolved
    country) takes precedence over an earlier verbatim one.
    """
    out: Dict[str, Any] = {}
    for key, value in record.items():
        target = DWC_OUTPUT_FIELD_MAP.get(key, key)
        if target in out:
            is_empty = value is None or str(value).strip() == ""
            if is_empty:
                continue
        out[target] = value
    return out


def to_dwc_records(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Apply :func:`to_dwc_record` to every record."""
    return [to_dwc_record(record) for record in records]
