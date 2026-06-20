"""Tests for inline deduplication in BatchProcessor.process_dataset.

These verify the GUI/CLI wiring: with deduplicate=True, only unique
locality/country targets are sent to the (stubbed) AI, but the returned records
cover every original row, each carrying its locality's georeference result.
"""

import placebot.core.batch_processor as bp_mod
from placebot.core.batch_processor import BatchProcessor
from placebot.core.field_mapping import get_locality


# An ai_test_dups.tsv-shaped set: 3x Krahi/Thailand, 2x Agadir/Morocco.
SAMPLE_RECORDS = [
    {"Barcode": "1", "Locality verbatim": "Krahi", "Country": "Thailand"},
    {"Barcode": "2", "Locality verbatim": "Agadir", "Country": "Morocco"},
    {"Barcode": "3", "Locality verbatim": "Krahi", "Country": "Thailand"},
    {"Barcode": "4", "Locality verbatim": "Krahi", "Country": "Thailand"},
    {"Barcode": "5", "Locality verbatim": "Agadir", "Country": "Morocco"},
]


def _build_processor(tmp_path, monkeypatch, processed_localities):
    """A BatchProcessor with all external collaborators stubbed out."""

    class StubDatasetManager:
        def load_dataset(self, info):
            return [dict(r) for r in SAMPLE_RECORDS]

        def create_output_filename(self, info, name):
            return str(tmp_path / "out.tsv")

    class StubOutputManager:
        def save_progress(self, recs, path, n):
            return path

        def save_final_results(self, recs, path):
            return True

        def generate_summary_report(self, *a, **k):
            return ""

    monkeypatch.setattr(bp_mod, "check_for_resume", lambda info: None)
    monkeypatch.setattr(bp_mod, "update_resume_state", lambda *a, **k: None)
    monkeypatch.setattr(bp_mod, "cleanup_resume_state", lambda *a, **k: None)
    monkeypatch.setattr(bp_mod, "AIProcessor", lambda cfg: object())

    def fake_process_batch(self, batch, ai_processor, progress_callback=None,
                           processed_offset=0, total=0):
        out = []
        for rec in batch:
            loc = get_locality(rec)
            processed_localities.append(loc)
            enriched = dict(rec)
            enriched["Latitude"] = f"lat::{loc}"
            enriched["Longitude"] = f"lon::{loc}"
            out.append(enriched)
        return out

    monkeypatch.setattr(BatchProcessor, "_process_batch", fake_process_batch)
    return BatchProcessor(StubDatasetManager(), StubOutputManager())


def test_process_dataset_dedup_expands_to_all_rows(tmp_path, monkeypatch):
    processed_localities = []
    proc = _build_processor(tmp_path, monkeypatch, processed_localities)

    result = proc.process_dataset(
        {"filename": "dups.tsv"}, {"name": "stub"},
        batch_size=8, save_progress=False, deduplicate=True,
    )

    assert result["success"]
    out = result["processed_records"]

    # Only the two unique localities were georeferenced...
    assert sorted(processed_localities) == ["Agadir", "Krahi"]

    # ...but every original row comes back, each with its locality's coordinates.
    assert [r["Barcode"] for r in out] == ["1", "2", "3", "4", "5"]
    assert [r["Latitude"] for r in out] == [
        "lat::Krahi", "lat::Agadir", "lat::Krahi", "lat::Krahi", "lat::Agadir",
    ]
    # Tracking columns from the collapse must not leak into the expanded output.
    assert all("placebotDedupKey" not in r for r in out)


def test_process_dataset_without_dedup_processes_every_row(tmp_path, monkeypatch):
    processed_localities = []
    proc = _build_processor(tmp_path, monkeypatch, processed_localities)

    result = proc.process_dataset(
        {"filename": "dups.tsv"}, {"name": "stub"},
        batch_size=8, save_progress=False, deduplicate=False,
    )

    assert result["success"]
    # Default behaviour unchanged: all five rows (including duplicates) processed.
    assert len(processed_localities) == 5
    assert len(result["processed_records"]) == 5
