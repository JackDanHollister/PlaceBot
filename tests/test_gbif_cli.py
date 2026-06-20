"""Tests for the GBIF/Darwin Core preparation workflow."""

import csv
from pathlib import Path

from placebot.cli.gbif import (
    dedup_key,
    deduplicate_records,
    expand_run,
    filter_records,
    has_valid_decimal_coordinates,
    needs_placebot_georeferencing,
    read_records,
    reconstitute_records,
    run,
)


def test_needs_placebot_georeferencing_for_missing_coordinates():
    record = {
        "occurrenceID": "gbif-demo-1",
        "verbatimLocality": "Monks Wood, Huntingdonshire",
        "country": "United Kingdom",
        "decimalLatitude": "",
        "decimalLongitude": "",
    }

    assert needs_placebot_georeferencing(record)


def test_skips_records_without_locality():
    record = {
        "occurrenceID": "gbif-demo-2",
        "country": "United Kingdom",
        "decimalLatitude": "",
        "decimalLongitude": "",
    }

    assert not needs_placebot_georeferencing(record)


def test_skips_valid_existing_coordinates_by_default():
    record = {
        "occurrenceID": "gbif-demo-3",
        "verbatimLocality": "Edinburgh",
        "decimalLatitude": "55.9533",
        "decimalLongitude": "-3.1883",
    }

    assert has_valid_decimal_coordinates(record)
    assert not needs_placebot_georeferencing(record)
    assert needs_placebot_georeferencing(record, include_existing=True)


def test_filter_records_counts_and_limits():
    records = [
        {"occurrenceID": "1", "verbatimLocality": "A", "decimalLatitude": "", "decimalLongitude": ""},
        {"occurrenceID": "2", "verbatimLocality": "B", "decimalLatitude": "", "decimalLongitude": ""},
        {"occurrenceID": "3", "verbatimLocality": "C", "decimalLatitude": "1", "decimalLongitude": "2"},
    ]

    selected, stats = filter_records(records, max_records=1)

    assert [record["occurrenceID"] for record in selected] == ["1"]
    assert stats["total"] == 3
    assert stats["with_locality"] == 3
    assert stats["with_valid_coordinates"] == 1
    assert stats["selected"] == 1
    assert stats["duplicates_removed"] == 0


def test_dedup_key_uses_locality_and_country():
    a = {"verbatimLocality": "  Warmond,  Sweilandpolder ", "country": "Netherlands"}
    b = {"locality": "warmond, sweilandpolder", "Country": " netherlands "}
    c = {"locality": "warmond, sweilandpolder", "country": "Belgium"}

    assert dedup_key(a) == dedup_key(b)
    assert dedup_key(a) != dedup_key(c)


def test_deduplicate_records_keeps_occurrence_ids_and_count():
    records = [
        {"occurrenceID": "occ-1", "verbatimLocality": "Warmond", "country": "Netherlands"},
        {"occurrenceID": "occ-2", "verbatimLocality": "Warmond", "country": "Netherlands"},
        {"occurrenceID": "occ-3", "verbatimLocality": "Paris", "country": "France"},
    ]

    deduped, duplicate_count = deduplicate_records(records)
    by_key = {record["placebotDedupKey"]: record for record in deduped}

    assert duplicate_count == 1
    assert len(deduped) == 2
    warmond = by_key["warmond|netherlands"]
    assert warmond["placebotOccurrenceIDs"] == "occ-1|occ-2"
    assert warmond["placebotOccurrenceCount"] == "2"


def test_run_writes_candidate_file(tmp_path):
    input_path = tmp_path / "gbif.csv"
    output_path = tmp_path / "candidates.tsv"
    rows = [
        {
            "occurrenceID": "gbif-demo-1",
            "verbatimLocality": "Monks Wood",
            "country": "United Kingdom",
            "decimalLatitude": "",
            "decimalLongitude": "",
        },
        {
            "occurrenceID": "gbif-demo-2",
            "verbatimLocality": "Edinburgh",
            "country": "United Kingdom",
            "decimalLatitude": "55.9533",
            "decimalLongitude": "-3.1883",
        },
    ]
    with input_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    class Args:
        input = str(input_path)
        output = str(output_path)
        include_existing = False
        max_records = None
        no_deduplicate = False

    assert run(Args) == 0
    records, fieldnames, delimiter = read_records(output_path)

    assert delimiter == "\t"
    assert fieldnames == list(rows[0].keys()) + [
        "placebotDedupKey",
        "placebotOccurrenceIDs",
        "placebotOccurrenceCount",
    ]
    assert len(records) == 1
    assert records[0]["occurrenceID"] == "gbif-demo-1"
    assert records[0]["placebotOccurrenceIDs"] == "gbif-demo-1"


def test_real_gbif_example_is_placebot_ready():
    sample = Path("examples/gbif_occurrence_real_sample.csv")
    records, _fieldnames, _delimiter = read_records(sample)

    selected, stats = filter_records(records)

    assert stats["total"] == 30
    assert stats["with_locality"] == 30
    assert stats["with_valid_coordinates"] == 0
    assert stats["selected"] == 30
    assert stats["duplicates_removed"] == 6
    assert len(selected) == 24
    assert any(record["placebotOccurrenceCount"] == "3" for record in selected)
    assert all(record["license"].endswith("/publicdomain/zero/1.0/legalcode") for record in selected)


def test_real_gbif_example_can_skip_deduplication():
    sample = Path("examples/gbif_occurrence_real_sample.csv")
    records, _fieldnames, _delimiter = read_records(sample)

    selected, stats = filter_records(records, deduplicate=False)

    assert stats["selected"] == 30
    assert stats["duplicates_removed"] == 0
    assert len(selected) == 30


def test_reconstitute_records_reattaches_results_to_every_occurrence():
    original = [
        {"occurrenceID": "occ-1", "verbatimLocality": "Warmond", "country": "Netherlands"},
        {"occurrenceID": "occ-2", "verbatimLocality": "Warmond", "country": "Netherlands"},
        {"occurrenceID": "occ-3", "verbatimLocality": "Paris", "country": "France"},
    ]
    processed = [
        {
            "verbatimLocality": "Warmond",
            "country": "Netherlands",
            "Latitude": "52.2",
            "Longitude": "4.5",
            "Confidence": "high",
        },
        {
            "verbatimLocality": "Paris",
            "country": "France",
            "Latitude": "48.85",
            "Longitude": "2.35",
            "Confidence": "medium",
        },
    ]

    expanded, stats = reconstitute_records(original, processed)

    assert stats == {"total": 3, "matched": 3, "unmatched": 0}
    assert [row["occurrenceID"] for row in expanded] == ["occ-1", "occ-2", "occ-3"]
    # Both Warmond occurrences receive the same georeference result.
    assert expanded[0]["Latitude"] == "52.2"
    assert expanded[1]["Latitude"] == "52.2"
    assert expanded[2]["Latitude"] == "48.85"


def test_reconstitute_records_marks_unmatched_occurrences():
    original = [
        {"occurrenceID": "occ-1", "verbatimLocality": "Warmond", "country": "Netherlands"},
        {"occurrenceID": "occ-2", "verbatimLocality": "Nowhere", "country": "Atlantis"},
    ]
    processed = [
        {"verbatimLocality": "Warmond", "country": "Netherlands", "Latitude": "52.2"},
    ]

    expanded, stats = reconstitute_records(original, processed)

    assert stats == {"total": 2, "matched": 1, "unmatched": 1}
    assert expanded[0]["Latitude"] == "52.2"
    assert "Latitude" not in expanded[1]


def test_prep_then_expand_round_trip(tmp_path):
    """A deduplicated prep file, once processed, expands back to every row."""
    original = [
        {"occurrenceID": "occ-1", "verbatimLocality": "Warmond", "country": "Netherlands",
         "decimalLatitude": "", "decimalLongitude": ""},
        {"occurrenceID": "occ-2", "verbatimLocality": "Warmond", "country": "Netherlands",
         "decimalLatitude": "", "decimalLongitude": ""},
        {"occurrenceID": "occ-3", "verbatimLocality": "Paris", "country": "France",
         "decimalLatitude": "", "decimalLongitude": ""},
    ]
    original_path = tmp_path / "original.csv"
    with original_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(original[0].keys()))
        writer.writeheader()
        writer.writerows(original)

    # Prep collapses the two Warmond rows into one candidate.
    candidates, _ = filter_records(original)
    assert len(candidates) == 2

    # Simulate PlaceBot georeferencing each unique candidate.
    processed = []
    for record in candidates:
        result = dict(record)
        result["Latitude"] = "1.0"
        result["Longitude"] = "2.0"
        processed.append(result)
    processed_path = tmp_path / "processed.tsv"
    with processed_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(processed[0].keys()), delimiter="\t")
        writer.writeheader()
        writer.writerows(processed)

    output_path = tmp_path / "final.tsv"

    class Args:
        original = str(original_path)
        processed = str(processed_path)
        output = str(output_path)
        dwc = False

    assert expand_run(Args) == 0
    rows, fieldnames, delimiter = read_records(output_path)

    assert delimiter == "\t"
    assert len(rows) == 3
    assert [row["occurrenceID"] for row in rows] == ["occ-1", "occ-2", "occ-3"]
    assert all(row["Latitude"] == "1.0" for row in rows)
    assert "Latitude" in fieldnames
