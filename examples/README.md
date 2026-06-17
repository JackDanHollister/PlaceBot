# PlaceBot Example Datasets

This directory contains small files for smoke testing PlaceBot after
installation.

## Files

| File | Records | Purpose |
| --- | ---: | --- |
| `ai_test.tsv` | 4 | Minimal native PlaceBot TSV with `Barcode`, `Locality verbatim`, and `Country` columns. |
| `dwc_test.csv` | 3 | Minimal Darwin Core CSV for checking DwC input mapping. |

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
