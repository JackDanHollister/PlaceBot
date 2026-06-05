"""Shared pytest fixtures for the PlaceBot test suite."""

import pytest


@pytest.fixture
def sample_records():
    """A small set of processed-style records for formatter/preview tests."""
    return [
        {
            "Barcode": "1",
            "Locality verbatim": "California, San Francisco, Golden Gate Park",
            "Country": "USA",
            "Latitude": 37.7694,
            "Longitude": -122.4862,
            "Confidence": "high",
            "Coordinate_Source": "estimated",
        },
        {
            "Barcode": "2",
            "Locality verbatim": "Unknown place with no coordinates",
            "Country": "",
            "Latitude": None,
            "Longitude": None,
            "Confidence": "low",
            "Coordinate_Source": "no_coordinates",
        },
    ]


@pytest.fixture
def tsv_dataset(tmp_path):
    """Write a tiny TSV dataset and return its path."""
    path = tmp_path / "localities.tsv"
    path.write_text(
        "Barcode\tLocality verbatim\tCountry\n"
        "1\tGolden Gate Park\tUSA\n"
        "2\tEdinburgh, Royal Botanic Garden\tUK\n",
        encoding="utf-8",
    )
    return path


@pytest.fixture
def isolated_home(tmp_path, monkeypatch):
    """Point HOME at a temp dir so ~/.placebot writes are isolated."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    return tmp_path
