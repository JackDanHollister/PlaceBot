# PlaceBot for GBIF / Darwin Core

PlaceBot includes a built-in GBIF/Darwin Core georeferencing workflow. This
guide covers using it to improve biodiversity occurrence data — for example, for
the 2026 Ebbe Nielsen Challenge.

> The `placebot-prep` and `placebot-expand` commands described here are not
> GBIF-specific: they work on any locality-bearing dataset (native PlaceBot,
> Darwin Core, or GBIF). This guide frames them around GBIF occurrence data.

## What It Does

PlaceBot helps improve biodiversity occurrence data quality by selecting GBIF or
Darwin Core occurrence records that have usable locality text but missing or
invalid decimal coordinates, then running them through PlaceBot's georeferencing
workflow. Outputs can be exported with Darwin Core terms for curator review and
downstream reuse.

The goal is not to automatically overwrite published coordinates. It is to
produce auditable candidate georeferences with uncertainty and confidence fields
that data publishers can review before republishing improved occurrence data.

## Why It Fits GBIF

- Targets a common occurrence-data quality gap: records with
  `verbatimLocality` but missing or invalid `decimalLatitude` /
  `decimalLongitude`.
- Uses Darwin Core-compatible input and output terms.
- Supports local/offline Ollama models for low-cost, privacy-preserving review.
- Includes public benchmark datasets and archived model-comparison outputs.
- Provides an open, repeatable workflow that can be run from the GUI or CLI.

## GBIF Workflow

1. Download occurrence data from GBIF as CSV, choosing records where locality
   text is present and coordinates are missing, invalid, or worth reviewing.
2. Keep the GBIF download DOI or query URL for citation in any submission.
3. Prepare a PlaceBot candidate file:

```bash
placebot-prep path/to/gbif_occurrence.csv \
  --output ~/.placebot/input/gbif_placebot_candidates.tsv
```

4. Launch the GUI:

```bash
placebot-gui
```

5. Select `gbif_placebot_candidates.tsv`, choose a local or cloud model, and
   tick Darwin Core output when exporting.
6. Review output columns such as `decimalLatitude`, `decimalLongitude`,
   `coordinateUncertaintyInMeters`, and georeferencing remarks before using
   them to improve a source dataset.
7. Reconstitute the results back onto every original occurrence (the
   deduplication in step 3 collapses repeated localities, so each unique place
   is georeferenced once and then re-expanded):

```bash
placebot-expand \
  --original path/to/gbif_occurrence.csv \
  --processed path/to/placebot_results.tsv \
  --output ~/.placebot/output/gbif_georeferenced.csv
```

For a small local dry run of the preparation step:

```bash
placebot-prep examples/gbif_occurrence_sample.csv \
  --output /tmp/gbif_placebot_candidates.tsv
```

For a real-data smoke test from GBIF-mediated records:

```bash
placebot-prep examples/gbif_occurrence_real_sample.csv \
  --output /tmp/gbif_real_placebot_candidates.tsv
```

`examples/gbif_occurrence_real_sample.csv` contains 30 CC0
`PRESERVED_SPECIMEN` records retrieved from the GBIF occurrence API with
`hasCoordinate=false`, then locally filtered to rows with locality text. See
`examples/gbif_occurrence_real_sample_README.md` for the exact source query and
limitations.

## The Preparation Command

`placebot-prep` reads CSV, TSV, or TXT files and writes the subset of
records that PlaceBot should georeference. By default, it deduplicates repeated
locality/country targets so PlaceBot georeferences each unique place string only
once. The output keeps `placebotOccurrenceIDs`, `placebotOccurrenceCount`, and
`placebotDedupKey` columns so the candidate georeference can be traced back to
all original occurrences that shared that text.

By default it includes records that:

- have locality text (`verbatimLocality`, `locality`, `Locality verbatim`, or
  `label_verbatim`), and
- do not have valid decimal coordinates.

Useful options:

```bash
# Include already-coordinate records too, useful for audit or benchmarking
placebot-prep occurrences.csv --include-existing

# Create a small demo file from a large GBIF download
placebot-prep occurrences.csv --max-records 50

# Keep every occurrence row, even when locality/country strings repeat
placebot-prep occurrences.csv --no-deduplicate
```

## Reconstituting Results

`placebot-expand` reverses the deduplication after PlaceBot has
georeferenced the candidate file. It joins the full original occurrence file
against PlaceBot's results on the same locality/country key used to collapse
them, then copies the georeference columns (`Latitude`, `Longitude`,
`Coordinate_Radius_Meters`, `Confidence`, georeferencing remarks, and the
resolved place hierarchy) onto **every** original occurrence — so each of the
duplicates that shared a locality receives the same candidate georeference.

```bash
placebot-expand \
  --original path/to/gbif_occurrence.csv \
  --processed path/to/placebot_results.tsv \
  --output path/to/gbif_georeferenced.csv

# Rename produced columns to Darwin Core terms in the output
placebot-expand --original occurrences.csv --processed results.tsv --dwc
```

The join uses locality plus country, so it works even if the
`placebotOccurrenceIDs` tracking columns were dropped during processing; those
columns remain useful as an audit trail of which occurrences shared a target.

## Submission Notes

For the challenge submission, the demo should use a real GBIF occurrence
download and cite its DOI. The bundled `examples/gbif_occurrence_sample.csv`
is only a tiny synthetic file that demonstrates the expected Darwin Core shape.
The bundled `examples/gbif_occurrence_real_sample.csv` is real GBIF-mediated
data, but it comes from the occurrence API rather than a formal GBIF download;
use it for workflow testing, then create a DOI-backed GBIF download for the
final submission.
