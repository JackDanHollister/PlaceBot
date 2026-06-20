# Real GBIF Occurrence Sample

This file is a small real-data smoke-test extract from the GBIF occurrence API,
created on 2026-06-19 13:17:41 UTC.

Source query:

```text
https://api.gbif.org/v1/occurrence/search?basisOfRecord=PRESERVED_SPECIMEN&hasCoordinate=false&license=CC0_1_0&limit=100
```

Selection criteria:

- `basisOfRecord=PRESERVED_SPECIMEN`
- `hasCoordinate=false`
- `license=CC0_1_0`
- records retained locally only when `locality` or `verbatimLocality` was present

The sample is intended for testing the prep/expand workflow with
`placebot-prep`. It is not a formal GBIF download and does not have a GBIF
DOI. For production use, create a proper GBIF download and cite its DOI.

Each row includes `gbifApiUrl` so records can be inspected through the GBIF API.
