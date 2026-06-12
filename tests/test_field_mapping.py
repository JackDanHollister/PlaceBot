"""Tests for Darwin Core (DwC) aware input resolution and output mapping."""

from placebot.core.field_mapping import (
    get_ai_locality,
    get_country,
    get_existing_coordinates,
    get_identifier,
    get_locality,
    has_identifier_column,
    has_locality_column,
    to_dwc_record,
    to_dwc_records,
)
from placebot.core.output_formatter import OutputFormatter


# ---------------------------------------------------------------------------
# Input resolution
# ---------------------------------------------------------------------------

def test_native_columns_still_resolve():
    """Existing PlaceBot column names must behave exactly as before."""
    record = {
        "Barcode": "10577259",
        "Locality verbatim": "Monks Wood, Hunts., England",
        "Country": "United Kingdom",
    }
    assert get_identifier(record) == "10577259"
    assert get_locality(record) == "Monks Wood, Hunts., England"
    assert get_country(record) == "United Kingdom"


def test_darwin_core_columns_resolve():
    """Darwin Core terms are recognised as aliases for the same concepts."""
    record = {
        "collectionID": "ABC123",
        "verbatimLocality": "Monks Wood, Hunts.",
        "country": "United Kingdom",
    }
    assert get_identifier(record) == "ABC123"
    assert get_locality(record) == "Monks Wood, Hunts."
    assert get_country(record) == "United Kingdom"


def test_native_name_wins_over_dwc_when_both_present():
    """Native names come first in the alias list, so they take precedence."""
    record = {"Locality verbatim": "native", "verbatimLocality": "dwc"}
    assert get_locality(record) == "native"


def test_identifier_default_when_missing():
    assert get_identifier({}, default="record_0") == "record_0"


def test_decimal_coordinates_resolved_from_dwc():
    record = {"decimalLatitude": "52.4", "decimalLongitude": "-0.2"}
    assert get_existing_coordinates(record) == ("52.4", "-0.2")


def test_empty_values_are_skipped():
    """Blank native columns fall through to the next alias."""
    record = {"Country": "  ", "country": "France"}
    assert get_country(record) == "France"


def test_verbatim_coordinates_appended_for_ai_only():
    """Verbatim coords are surfaced to the AI but not to the plain locality."""
    record = {
        "verbatimLocality": "Monks Wood",
        "verbatimLatitude": "52 24N",
        "verbatimLongitude": "0 14W",
    }
    assert get_locality(record) == "Monks Wood"
    ai_text = get_ai_locality(record)
    assert "Monks Wood" in ai_text
    assert "52 24N 0 14W" in ai_text


def test_verbatim_coordinates_skipped_when_decimal_present():
    """If parseable decimal coords exist, don't clutter the AI text."""
    record = {
        "verbatimLocality": "Monks Wood",
        "decimalLatitude": "52.4",
        "decimalLongitude": "-0.2",
        "verbatimCoordinates": "ignored",
    }
    assert get_ai_locality(record) == "Monks Wood"


def test_verbatim_coordinates_field_alone():
    record = {"verbatimLocality": "Site", "verbatimCoordinates": "41 05S 121 05W"}
    assert "41 05S 121 05W" in get_ai_locality(record)


# ---------------------------------------------------------------------------
# Input detection
# ---------------------------------------------------------------------------

def test_has_locality_column_detects_dwc():
    assert has_locality_column(["collectionID", "verbatimLocality", "country"])
    assert has_locality_column(["Locality verbatim"])
    assert not has_locality_column(["catalogNumber", "country"])


def test_has_identifier_column_detects_dwc():
    assert has_identifier_column(["collectionID", "verbatimLocality"])
    assert has_identifier_column(["Barcode"])
    assert has_identifier_column(["occurrenceID"])


# ---------------------------------------------------------------------------
# Output mapping
# ---------------------------------------------------------------------------

def test_to_dwc_record_renames_produced_columns():
    record = {
        "Barcode": "B1",
        "Exact_Site": "Paris",
        "State": "Ile-de-France",
        "Latitude": 48.85,
        "Longitude": 2.35,
        "Coordinate_Radius_Meters": 100,
    }
    out = to_dwc_record(record)
    assert out["catalogNumber"] == "B1"
    assert out["locality"] == "Paris"
    assert out["stateProvince"] == "Ile-de-France"
    assert out["decimalLatitude"] == 48.85
    assert out["decimalLongitude"] == 2.35
    assert out["coordinateUncertaintyInMeters"] == 100


def test_processed_country_wins_over_verbatim_country():
    """Country and Country_Processed both map to 'country'; processed wins."""
    record = {"Country": "verbatim", "Country_Processed": "France"}
    assert to_dwc_record(record)["country"] == "France"


def test_empty_processed_country_keeps_verbatim():
    record = {"Country": "France", "Country_Processed": ""}
    assert to_dwc_record(record)["country"] == "France"


def test_unmapped_columns_pass_through():
    record = {"custom_field": "value", "Latitude": 1.0}
    out = to_dwc_record(record)
    assert out["custom_field"] == "value"
    assert "decimalLatitude" in out


def test_to_dwc_records_applies_to_all():
    records = [{"Latitude": 1.0}, {"Latitude": 2.0}]
    out = to_dwc_records(records)
    assert all("decimalLatitude" in r for r in out)


# ---------------------------------------------------------------------------
# Output formatter integration
# ---------------------------------------------------------------------------

_SAMPLE = [{
    "Barcode": "B1",
    "Country_Processed": "France",
    "Exact_Site": "Paris",
    "Latitude": 48.85,
    "Longitude": 2.35,
}]


def test_csv_bytes_dwc_header():
    header = OutputFormatter.records_to_csv_bytes(_SAMPLE, dwc=True).decode("utf-8-sig").splitlines()[0]
    columns = header.split(",")
    assert "decimalLatitude" in columns
    assert "catalogNumber" in columns
    assert "Latitude" not in columns


def test_csv_bytes_native_unchanged():
    header = OutputFormatter.records_to_csv_bytes(_SAMPLE).decode("utf-8-sig").splitlines()[0]
    columns = header.split(",")
    assert "Latitude" in columns
    assert "decimalLatitude" not in columns


def test_geojson_dwc_excludes_decimal_coords_from_properties():
    import json

    gj = json.loads(OutputFormatter.records_to_geojson_bytes(_SAMPLE, dwc=True).decode("utf-8"))
    feature = gj["features"][0]
    assert feature["geometry"]["coordinates"] == [2.35, 48.85]
    assert "decimalLatitude" not in feature["properties"]
    assert "decimalLongitude" not in feature["properties"]
    assert feature["properties"]["locality"] == "Paris"


def test_write_output_dwc(tmp_path):
    written = OutputFormatter.write_output(_SAMPLE, str(tmp_path / "out"), ["csv"], dwc=True)
    content = open(written["csv"], encoding="utf-8-sig").read()
    assert "decimalLatitude" in content.splitlines()[0]
