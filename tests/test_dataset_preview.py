"""Tests for dataset preview statistics."""

from placebot.core.dataset_preview import DatasetPreview


def test_statistics_on_empty_data():
    stats = DatasetPreview.get_statistics([])
    assert stats["has_data"] is False
    assert stats["total_records"] == 0


def test_statistics_detects_locality():
    data = [{"Barcode": "1", "Locality verbatim": "somewhere nice"}]
    stats = DatasetPreview.get_statistics(data)
    assert stats["has_data"] is True
    assert stats["has_locality"] is True
    assert stats["total_records"] == 1


def test_statistics_handles_none_field_names():
    # csv.DictReader yields a None key for ragged rows; must not crash
    data = [{"Barcode": "1", "Locality verbatim": "x", None: ["extra", "cols"]}]
    stats = DatasetPreview.get_statistics(data)
    assert stats["has_data"] is True


def test_get_sample_records_caps_at_dataset_size():
    data = [{"id": i} for i in range(3)]
    assert len(DatasetPreview.get_sample_records(data, 10)) == 3
