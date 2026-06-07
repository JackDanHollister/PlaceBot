"""Tests for staggered (async) batch helpers and GUI job listing."""

import json
import os

from placebot.core.data_dirs import setup_directories, get_batch_jobs_dir
from placebot.cli.batch_download_staggered import fetch_staggered_results


def _write(path, payload):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f)


def test_fetch_staggered_results_missing_file(isolated_home):
    res = fetch_staggered_results("/no/such/summary.json")
    assert res["success"] is False
    assert "not found" in res["error"].lower()


def test_list_batch_jobs_collapses_subbatches(isolated_home):
    # Importing the GUI module requires Streamlit (installed via the gui extra).
    from placebot.gui import app

    setup_directories()
    bd = str(get_batch_jobs_dir())

    # A single (non-staggered) batch job.
    _write(
        os.path.join(bd, "ds_model_111_info.json"),
        {
            "batch_id": "single-1",
            "batch_name": "ds_model_111",
            "provider": "anthropic",
            "model": "claude",
            "record_count": 50,
            "submitted_at": "20260606_120000",
            "output_formats": ["csv"],
        },
    )

    # A staggered job: master summary + two sub-batch info files.
    _write(
        os.path.join(bd, "big_gemini_222_staggered_summary.json"),
        {
            "total_records": 1000,
            "batches_submitted": 2,
            "provider": "gemini",
            "model": "gemini",
            "submitted_at": "20260606_130000",
            "output_formats": ["csv", "json"],
            "batches": [
                {"batch_number": 1, "batch_id": "sub-a", "record_count": 500},
                {"batch_number": 2, "batch_id": "sub-b", "record_count": 500},
            ],
        },
    )
    _write(
        os.path.join(bd, "big_gemini_222_batch1of2_info.json"),
        {"batch_number": 1, "batch_id": "sub-a", "batch_name": "big_b1"},
    )
    _write(
        os.path.join(bd, "big_gemini_222_batch2of2_info.json"),
        {"batch_number": 2, "batch_id": "sub-b", "batch_name": "big_b2"},
    )

    jobs = app._list_batch_jobs()
    # Two jobs: the single batch and the staggered summary. Sub-batches hidden.
    assert len(jobs) == 2
    by_type = {j["type"]: j for j in jobs}
    assert set(by_type) == {"single", "staggered"}
    assert by_type["staggered"]["batches_submitted"] == 2
    assert by_type["staggered"]["record_count"] == 1000
    assert by_type["single"]["batch_id"] == "single-1"


def test_stagger_profiles_cover_each_provider():
    from placebot.gui import app

    assert app._stagger_profile("google gemini") == (500, 120)
    assert app._stagger_profile("anthropic claude") == (1000, 30)
    assert app._stagger_profile("openai gpt") == (2000, 10)
    assert app._stagger_profile("qwen local") is None
