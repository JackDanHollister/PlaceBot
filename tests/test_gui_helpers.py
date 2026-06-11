"""Tests for the GUI's pure helper functions (no Streamlit runtime needed)."""

import json

from placebot.gui import app
from placebot.gui import launcher


def test_csv_bytes_has_header_and_rows(sample_records):
    raw = app.records_to_csv_bytes(sample_records)
    # CSV is emitted with a UTF-8 BOM so Excel renders accents correctly.
    assert raw.startswith(b"\xef\xbb\xbf")
    text = raw.decode("utf-8-sig")
    lines = text.splitlines()
    # Canonical column order puts Barcode first.
    assert lines[0].startswith("Barcode")
    assert len(lines) == 3  # header + 2 records


def test_csv_bytes_consistent_column_order(sample_records):
    # Columns follow the shared canonical order regardless of dict insertion.
    text = app.records_to_csv_bytes(sample_records).decode("utf-8-sig")
    header = text.splitlines()[0]
    assert header.split(",")[:5] == [
        "Barcode",
        "Locality verbatim",
        "Country",
        "Latitude",
        "Longitude",
    ]


def test_json_bytes_roundtrips(sample_records):
    data = json.loads(app.records_to_json_bytes(sample_records))
    assert len(data) == 2
    assert data[0]["Barcode"] == "1"


def test_geojson_skips_records_without_coords(sample_records):
    gj = json.loads(app.records_to_geojson_bytes(sample_records))
    assert gj["type"] == "FeatureCollection"
    # Only the first record has coordinates
    assert len(gj["features"]) == 1
    # GeoJSON order is [lon, lat]
    assert gj["features"][0]["geometry"]["coordinates"] == [-122.4862, 37.7694]


def test_model_needs_key_logic():
    assert app._model_needs_key({"name": "Claude Haiku 4.5", "provider": "Anthropic"})
    assert not app._model_needs_key({"name": "Qwen 3 8B (local)", "provider": "Ollama"})


def test_model_has_key_for_local_without_key():
    assert app._model_has_key(
        {
            "name": "Qwen 3 8B (local)",
            "provider": "Ollama",
            "api_key": "",
            "local_ready": True,
        }
    )
    assert not app._model_has_key(
        {
            "name": "Qwen 3 8B (local)",
            "provider": "Ollama",
            "api_key": "",
            "local_ready": False,
        }
    )
    assert not app._model_has_key(
        {"name": "Claude", "provider": "Anthropic", "api_key": ""}
    )


def test_processing_counts_detects_failed_rows():
    records = [
        {"Processing_Notes": "", "Coordinate_Source": "ai"},
        {"Processing_Notes": "AI processing failed: API error: 404"},
        {"Processing_Notes": "ok | Error: model missing"},
        {"Coordinate_Source": "failed"},
    ]
    assert app._processing_counts(records) == {
        "total": 4,
        "failed": 3,
        "successful": 1,
    }


def test_safe_uploaded_filename_strips_paths_and_unsafe_chars():
    assert app._safe_uploaded_filename("../../secret.csv") == "secret.csv"
    assert app._safe_uploaded_filename("..hidden.tsv") == "hidden.tsv"
    assert app._safe_uploaded_filename("my/data:export?.csv") == "data_export_.csv"
    assert app._safe_uploaded_filename("") == "uploaded_file"


def test_gui_launcher_binds_to_loopback_only():
    argv = launcher._streamlit_argv("/tmp/app.py")
    assert argv[0:3] == ["streamlit", "run", "/tmp/app.py"]
    assert argv[argv.index("--server.address") + 1] == "127.0.0.1"
