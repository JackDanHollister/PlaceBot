"""Tests for ensemble analysis (comparing two model output files)."""

import csv
import json

from placebot.core import ensemble_analysis as ea
from placebot.core.output_formatter import OutputFormatter


def test_haversine_known_distance():
    # ~1.11 km between two points 0.01 deg of latitude apart near Bristol.
    d = float(ea.haversine_distance(51.45, -2.59, 51.46, -2.59))
    assert 1.0 < d < 1.3


def test_categorise_boundaries():
    assert ea.categorise(0.0) == ea.CATEGORY_CLOSE
    assert ea.categorise(1.99) == ea.CATEGORY_CLOSE
    assert ea.categorise(2.0) == ea.CATEGORY_MODERATE
    assert ea.categorise(4.99) == ea.CATEGORY_MODERATE
    assert ea.categorise(5.0) == ea.CATEGORY_LOW
    assert ea.categorise(9.99) == ea.CATEGORY_LOW
    assert ea.categorise(10.0) == ea.CATEGORY_NONE
    assert ea.categorise(None) == ea.CATEGORY_NO_COMPARISON


def _write_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def test_run_ensemble_categories_and_carry_forward(tmp_path):
    primary = tmp_path / "p.csv"
    secondary = tmp_path / "s.json"

    _write_csv(
        primary,
        [
            {
                "Barcode": "1",
                "Locality verbatim": "A",
                "Latitude": "51.45",
                "Longitude": "-2.59",
            },
            {
                "Barcode": "2",
                "Locality verbatim": "B",
                "Latitude": "51.50",
                "Longitude": "-0.12",
            },
            {
                "Barcode": "3",
                "Locality verbatim": "C",
                "Latitude": "40.0",
                "Longitude": "-3.0",
            },
            {"Barcode": "4", "Locality verbatim": "D", "Latitude": "", "Longitude": ""},
            {
                "Barcode": "5",
                "Locality verbatim": "E",
                "Latitude": "10.0",
                "Longitude": "10.0",
            },
        ],
    )
    secondary.write_text(
        json.dumps(
            [
                {"Barcode": "1", "Latitude": 51.46, "Longitude": -2.59},  # close
                {"Barcode": "2", "Latitude": 51.527, "Longitude": -0.12},  # moderate
                {
                    "Barcode": "2",
                    "Latitude": 99.9,
                    "Longitude": 99.9,
                },  # duplicate -> ignored
                {"Barcode": "3", "Latitude": 51.0, "Longitude": -1.0},  # none
                {
                    "Barcode": "4",
                    "Latitude": 51.0,
                    "Longitude": -1.0,
                },  # primary missing
                {
                    "Barcode": "6",
                    "Latitude": 1.0,
                    "Longitude": 1.0,
                },  # only in secondary
            ]
        ),
        encoding="utf-8",
    )

    result = ea.run_ensemble(str(primary), str(secondary))

    assert result["total"] == 5
    assert result["only_in_primary"] == 1  # barcode 5
    assert result["only_in_secondary"] == 1  # barcode 6
    assert result["duplicate_barcodes"] == 1

    by_barcode = {r["Barcode"]: r for r in result["records"]}
    assert by_barcode["1"][ea.AGREEMENT_COLUMN] == ea.CATEGORY_CLOSE
    assert by_barcode["2"][ea.AGREEMENT_COLUMN] == ea.CATEGORY_MODERATE
    assert by_barcode["3"][ea.AGREEMENT_COLUMN] == ea.CATEGORY_NONE
    assert by_barcode["4"][ea.AGREEMENT_COLUMN] == ea.CATEGORY_NO_COMPARISON
    assert by_barcode["5"][ea.AGREEMENT_COLUMN] == ea.CATEGORY_NO_COMPARISON

    # Primary values are carried forward, secondary georef columns kept (prefixed).
    assert by_barcode["1"]["Locality verbatim"] == "A"
    assert by_barcode["1"][ea.SECONDARY_LAT_COLUMN] == 51.46
    assert by_barcode["1"]["Secondary_Longitude"] == -2.59
    assert by_barcode["5"][ea.SECONDARY_LAT_COLUMN] == ""  # only-in-primary -> blank
    assert by_barcode["4"][ea.DISTANCE_COLUMN] == ""  # no comparison -> blank

    summary = result["summary"]
    assert summary[ea.CATEGORY_CLOSE] == 1
    assert summary[ea.CATEGORY_MODERATE] == 1
    assert summary[ea.CATEGORY_LOW] == 0
    assert summary[ea.CATEGORY_NONE] == 1
    assert summary[ea.CATEGORY_NO_COMPARISON] == 2


def test_column_order_and_secondary_georef_only(tmp_path):
    primary = tmp_path / "p.csv"
    secondary = tmp_path / "s.csv"

    # Primary keeps its existing column order (incl. a non-georef input column).
    _write_csv(
        primary,
        [{
            "Barcode": "1",
            "scientificName": "Aus bus",
            "Latitude": "51.45",
            "Longitude": "-2.59",
            "Confidence": "high",
        }],
    )
    # Secondary has a georef column (Latitude/Longitude/Confidence) plus a
    # non-georef column (scientificName) that must NOT be carried.
    _write_csv(
        secondary,
        [{
            "Barcode": "1",
            "scientificName": "Aus bus",
            "Latitude": "51.46",
            "Longitude": "-2.59",
            "Confidence": "low",
        }],
    )

    result = ea.run_ensemble(str(primary), str(secondary))

    assert result["column_order"] == [
        "Barcode", "scientificName", "Latitude", "Longitude", "Confidence",
        "Secondary_Latitude", "Secondary_Longitude", "Secondary_Confidence",
        ea.AGREEMENT_COLUMN, ea.DISTANCE_COLUMN,
    ]

    rec = result["records"][0]
    # Secondary georef columns carried (prefixed); secondary non-georef dropped.
    assert rec["Secondary_Confidence"] == "low"
    assert "Secondary_scientificName" not in rec
    assert "Secondary_Barcode" not in rec

    # The CSV writer honours the explicit column order in the header.
    raw = OutputFormatter.records_to_csv_bytes(
        result["records"], column_order=result["column_order"]
    )
    header = raw.decode("utf-8-sig").splitlines()[0]
    assert header == ",".join(result["column_order"])


def test_summary_lists_every_category_including_zero():
    summary = ea.summarise([])
    assert list(summary.keys()) == ea.CATEGORIES
    assert all(v == 0 for v in summary.values())


def test_load_records_handles_tsv_and_geojson(tmp_path):
    tsv = tmp_path / "out.tsv"
    tsv.write_text("Barcode\tLatitude\tLongitude\n1\t1.0\t2.0\n", encoding="utf-8")
    recs = ea.load_records(str(tsv))
    assert recs == [{"Barcode": "1", "Latitude": "1.0", "Longitude": "2.0"}]

    gj = tmp_path / "out.geojson"
    gj.write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": {"type": "Point", "coordinates": [2.0, 1.0]},
                        "properties": {"Barcode": "1"},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    recs = ea.load_records(str(gj))
    assert recs[0]["Barcode"] == "1"
    assert recs[0]["Latitude"] == 1.0
    assert recs[0]["Longitude"] == 2.0


def test_tsv_writer_has_bom_and_tabs():
    raw = OutputFormatter.records_to_tsv_bytes(
        [{"Barcode": "1", "Latitude": 1.0, "Longitude": 2.0}]
    )
    assert raw.startswith(b"\xef\xbb\xbf")
    text = raw.decode("utf-8-sig")
    assert "\t" in text.splitlines()[0]
    assert text.splitlines()[0].startswith("Barcode")
