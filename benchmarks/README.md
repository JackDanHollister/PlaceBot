# Benchmark Datasets

This directory contains the supplementary benchmark data used around the
PlaceBot paper analyses. The paper and earlier project notes often refer to
these as the "700 Bombus" and "900 Odonata" datasets; the files here use the
exact available row counts from the archived project data.

## Files

| File | Records | Description |
| --- | ---: | --- |
| `data/bombus_uk_reference.tsv` | 709 | Bombus locality records with manual reference coordinates and uncertainty radius. |
| `data/odonata_global_reference.tsv` | 908 | Odonata locality records with manual reference coordinates and uncertainty radius. |
| `results/bombus_uk_model_comparison.tsv` | 709 | Paper-era model outputs and distance/uncertainty comparisons for the Bombus benchmark. |
| `results/odonata_global_model_comparison.tsv` | 908 | Paper-era model outputs and distance/uncertainty comparisons for the Odonata benchmark. |

The reference files have six columns:

- `Barcode`: specimen or benchmark record identifier.
- `label_verbatim`: original locality text supplied to PlaceBot.
- `Country`: country context where available.
- `lat_manual` / `long_manual`: manual reference coordinates in decimal degrees.
- `radius_km_manual`: manual coordinate uncertainty radius in kilometres.

The result files keep those reference columns and add model-specific coordinate,
AI radius, confidence, distance, and within-radius comparison columns.

## Usage

Use the files under `data/` when you want to re-run PlaceBot:

```bash
placebot
```

Then choose real-time or batch mode, select a model, and load one of the
benchmark TSV files. The files under `results/` are archived comparison outputs
from the paper-era benchmark runs and are intended for inspection rather than as
fresh input files.

## Data Notes

These records were derived from public natural-history specimen locality data
used in the PlaceBot evaluation work. They are included here to make the
repository reviewable and to support reproducible benchmarking.
