"""Tests for batch result parsing and download output formatting."""

import json

from placebot.core.async_batch_processor import (
    _extract_gemini_text_from_dict,
    _strip_markdown_fences,
    _deep_collect_text,
    _extract_first_json_object,
)
from placebot.cli.batch_manager import _results_to_records
from placebot.core.output_formatter import OutputFormatter


def _parse_line(line):
    """Mirror the download parser: find the answer JSON anywhere in the result."""
    result = json.loads(line)
    for t in _deep_collect_text(result):
        parsed = _extract_first_json_object(_strip_markdown_fences(t))
        if parsed is not None:
            return parsed
    return None


def test_deep_parse_standard_thinking_and_odd_wrapper():
    standard = json.dumps({"key": "1", "response": {"candidates": [
        {"content": {"parts": [{"text": '{"latitude": 7.9}'}]}}]}})
    assert _parse_line(standard) == {"latitude": 7.9}

    # thinking model: non-text thought part before a fenced JSON answer
    thinking = json.dumps({"key": "2", "response": {"candidates": [
        {"content": {"parts": [{"thought": True}, {"text": '```json\n{"lat": 1}\n```'}]}}]}})
    assert _parse_line(thinking) == {"lat": 1}

    # extra nesting the targeted parser would miss -> deep search still finds it
    odd = json.dumps({"key": "3", "response": {"result": {"candidates": [
        {"content": {"parts": [{"text": '{"a": 1}'}]}}]}}})
    assert _parse_line(odd) == {"a": 1}


def test_extract_first_json_object_tolerates_prose_and_braces_in_strings():
    assert _extract_first_json_object('Here: {"x": 5} done') == {"x": 5}
    assert _extract_first_json_object('{"note": "has } brace", "n": 1}') == {"note": "has } brace", "n": 1}
    assert _extract_first_json_object("no json here") is None


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


def test_output_filename_not_truncated_by_dots_in_model_name():
    # Model names like "Gemini 3.1 Pro" put a dot in the path; with_suffix would
    # truncate it to ai_test_Gemini_3.csv. Append-based extension must not.
    import tempfile
    import os

    base = os.path.join(tempfile.mkdtemp(), "ai_test_Gemini_3.1_Pro_20260606_results")
    path = OutputFormatter.to_csv([{"Barcode": "1", "Latitude": 1.0, "Longitude": 2.0}], base)
    assert os.path.basename(path) == "ai_test_Gemini_3.1_Pro_20260606_results.csv"


def test_gemini_batch_generation_config_thinking_low_for_pro_only():
    # Build the config without constructing a real genai client
    from placebot.core.async_batch_processor import GeminiBatchProcessor

    pro = object.__new__(GeminiBatchProcessor)
    pro.model_id = "gemini-3.1-pro-preview"
    cfg = pro._generation_config()
    assert cfg["responseMimeType"] == "application/json"
    assert cfg["thinkingConfig"] == {"thinkingLevel": "low"}

    flash = object.__new__(GeminiBatchProcessor)
    flash.model_id = "gemini-3.5-flash"
    assert "thinkingConfig" not in flash._generation_config()


def test_gemini_pro_realtime_sets_low_thinking():
    import placebot.models.gemini_3_1_pro as pro
    cfg = pro.format_request("x")["generationConfig"]
    assert cfg["thinkingConfig"]["thinkingLevel"] == "low"
    assert cfg["responseMimeType"] == "application/json"
