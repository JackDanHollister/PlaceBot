"""Tests for batch result parsing and download output formatting."""

import json

from placebot.core.async_batch_processor import (
    _extract_gemini_text_from_dict,
    _strip_markdown_fences,
)
from placebot.cli.batch_manager import _results_to_records
from placebot.core.output_formatter import OutputFormatter


def test_extract_text_from_thinking_multipart():
    # Gemini thinking models can return a non-text "thought" part before the answer
    resp = {"candidates": [{"content": {"parts": [
        {"thought": True},
        {"text": '{"latitude": 7.9, "longitude": 98.4}'},
    ]}}]}
    assert _extract_gemini_text_from_dict(resp) == '{"latitude": 7.9, "longitude": 98.4}'


def test_extract_text_handles_content_as_list_and_missing():
    assert _extract_gemini_text_from_dict({"candidates": [{"content": [{"text": "hi"}]}]}) == "hi"
    assert _extract_gemini_text_from_dict({"candidates": [{"finishReason": "SAFETY"}]}) == ""
    assert _extract_gemini_text_from_dict(None) == ""
    assert _extract_gemini_text_from_dict({}) == ""


def test_strip_markdown_fences():
    assert _strip_markdown_fences('```json\n{"a":1}\n```') == '{"a":1}'
    assert _strip_markdown_fences('{"a":1}') == '{"a":1}'


def test_results_to_records_keeps_every_record_and_merges_source():
    results = [
        {"barcode": "1", "success": True, "country": "Thailand",
         "latitude": 7.9, "longitude": 98.4, "confidence": "high"},
        {"barcode": "2", "success": False, "error": "finishReason=MAX_TOKENS"},
    ]
    source = {
        "1": {"Barcode": "1", "Locality verbatim": "Krabi", "Country": "Thailand"},
        "2": {"Barcode": "2", "Locality verbatim": "Unknown", "Country": ""},
    }
    recs = _results_to_records(results, source)
    assert len(recs) == 2  # no record dropped, even the failed one
    assert recs[0]["Locality verbatim"] == "Krabi"  # merged from source
    assert recs[0]["Latitude"] == 7.9
    assert recs[1]["Confidence"] == "low"
    assert "failed" in recs[1]["Processing_Notes"].lower()


def test_geojson_accepts_capitalised_coords():
    data = [
        {"Barcode": "1", "Latitude": 7.9, "Longitude": 98.4},
        {"Barcode": "2", "Latitude": None, "Longitude": None},
    ]
    import tempfile
    import os

    out = os.path.join(tempfile.mkdtemp(), "x.geojson")
    OutputFormatter.to_geojson(data, out)
    gj = json.load(open(out, encoding="utf-8"))
    assert len(gj["features"]) == 1  # only the record with coords
    assert gj["features"][0]["geometry"]["coordinates"] == [98.4, 7.9]
