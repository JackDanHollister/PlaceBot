# PlaceBot Example Datasets

This directory contains small files for smoke testing PlaceBot after
installation.

## Files

| File | Records | Purpose |
| --- | ---: | --- |
| `ai_test.tsv` | 4 | Minimal native PlaceBot TSV with `Barcode`, `Locality verbatim`, and `Country` columns. |
| `dwc_test.csv` | 3 | Minimal Darwin Core CSV for checking DwC input mapping. |
| `gbif_occurrence_sample.csv` | 4 | Tiny synthetic GBIF/Darwin Core-shaped file for testing `placebot-gbif-prep`. |
| `gbif_occurrence_real_sample.csv` | 30 | Real CC0 GBIF occurrence API sample with locality text and missing coordinates. |

For the larger paper supplementary datasets, see
[`../benchmarks/`](../benchmarks/). Those files are intended for benchmarking
and review rather than quick installation checks.

## Quick Smoke Test

```bash
placebot
```

When prompted, choose real-time mode, select any configured model, and load
`examples/ai_test.tsv`. For Darwin Core input/output testing, use
`examples/dwc_test.csv`.

To test the GBIF preparation command:

```bash
placebot-gbif-prep examples/gbif_occurrence_sample.csv \
  --output /tmp/gbif_placebot_candidates.tsv
```

The command deduplicates repeated locality/country targets by default and keeps
the original occurrence IDs in `placebotOccurrenceIDs`.

For a real GBIF-mediated smoke test:

```bash
placebot-gbif-prep examples/gbif_occurrence_real_sample.csv \
  --output /tmp/gbif_real_placebot_candidates.tsv
```

After processing the candidate file with PlaceBot, reconstitute the results back
onto every original occurrence with `placebot-gbif-expand`:

```bash
placebot-gbif-expand \
  --original examples/gbif_occurrence_real_sample.csv \
  --processed /tmp/placebot_results.tsv \
  --output /tmp/gbif_real_georeferenced.tsv
```

## Expected Input Shape

PlaceBot accepts either its native column names:

```tsv
Barcode	Locality verbatim	Country
1	California, San Francisco Bay, Golden Gate Park	United States
```

or Darwin Core terms such as `catalogNumber`, `verbatimLocality`, `country`,
`decimalLatitude`, and `decimalLongitude`.

See the main [`README.md`](../README.md) for installation, model selection,
local Ollama setup, and output options.
