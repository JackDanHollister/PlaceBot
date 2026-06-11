# Changelog

All notable changes to PlaceBot will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **OpenRouter provider support.** The GUI and config now support an
  `OPENROUTER_API_KEY`, and PlaceBot ships OpenRouter profiles for GPT-5 mini,
  GPT-4.1, Gemini 3.5 Flash, Claude Haiku 4.5, Claude Sonnet 4.6, and Claude
  Opus 4.8. These use OpenRouter's OpenAI-compatible chat-completions endpoint
  so one key can route across multiple vendors in real-time mode.
- **Ensemble analysis.** Compare two model output files (CSV/TSV/JSON) for the
  same dataset to flag records for manual verification. Records are matched on
  `Barcode`, the haversine distance between the two coordinate estimates is
  computed, and each record is tagged with an agreement category — close
  (<2km), moderate (2-5km), low (5-10km), none (>10km), or "no comparison". The
  output TSV/CSV carry forward the chosen primary file's values plus
  `Agreement_Category`, `Distance_km`, and the secondary model's coordinates,
  and a summary reports the per-category counts. Available as the new
  `placebot-ensemble` command and the **Ensemble analysis** page in the GUI.
- **TSV output format.** `OutputFormatter` can now write tab-separated values
  (UTF-8 with BOM, same canonical column order as CSV); selectable as a `tsv`
  output format and downloadable in the GUI.
- **Dynamic local Ollama model discovery in the GUI.** Installed Ollama models
  are now added to the model picker automatically, so users can run whichever
  local models they already have rather than only the bundled Qwen profile
  names.
- **Dedicated local model picker in the GUI.** The processing setup page now
  has a `Local Ollama` model-source option with a direct selectbox for local
  models, plus ready/not-installed status for each discovered Ollama profile.
- **Always-visible local model setup in the GUI.** The sidebar now shows
  whether Ollama is reachable, lists installed local models, and gives the
  install/pull command when no local models are available.
- **Header "How to use" guide in the GUI.** A top-of-page button now opens
  step-by-step instructions for adding model access, choosing data, selecting
  processing settings, running jobs, and collecting results.

### Fixed
- **Repository cleanup for public review.** Removed an obsolete setup script,
  a duplicate logo asset, and an empty example CSV; aligned requirements and
  example benchmark wording with the current package and public README.
- **Public install documentation.** README and INSTALL now describe the current
  GitHub/source install route, and label PyPI plus one-click installer downloads
  as release-pipeline work rather than currently available public downloads.
- **GUI API-key handling is session-only by default.** Pasted Anthropic,
  OpenAI, Google/Gemini, and OpenRouter keys are now kept only in the running
  GUI session unless the user explicitly ticks **Remember on this computer**.
  Saved keys remain supported in `~/.placebot/.env`, written with owner-only
  permissions where supported, but the GUI no longer pre-fills saved Google
  keys into password fields and clearly labels session, saved, and externally
  supplied environment keys.
- **GUI upload filename hardening.** Dataset and ensemble uploads now write
  using basename-only, conservative filenames, preventing uploaded filenames
  from escaping the intended input/output folders.
- **GUI local server exposure.** The packaged `placebot-gui` launcher now binds
  Streamlit to `127.0.0.1` instead of relying on Streamlit defaults, keeping
  the desktop GUI local to the user's machine.
- **Local model readiness checks.** Local models are no longer treated as ready
  just because they do not require an API key. The GUI now checks whether
  Ollama is reachable and whether the selected model is installed, and shows the
  relevant `ollama pull ...` command when a bundled local profile is missing.
- **All-record failure visibility.** Real-time GUI runs now warn/error when
  processed output rows contain model/API failures, instead of always reporting
  a successful run because output files were written.
- **CI lint.** Removed an unused `pytest` import from the ensemble tests.

## [1.2.5] - 2026-06-06

### Fixed
- **Gemini 3.1 Pro batches intermittently returned no result for some records**
  (`finishReason=STOP`, no JSON). Pro is a reasoning model and, with no thinking
  control, spent the turn thinking instead of emitting the answer. Gemini
  requests now set `thinkingConfig.thinkingLevel="low"` for Pro (batch and
  real-time) so it reliably returns the structured answer. Flash is unchanged.
- **Batch status used the wrong state enum.** The live API returns
  `BATCH_STATE_*` names but the code checked `JOB_STATE_SUCCEEDED`, so a
  completed batch could read as "not ready" and a running one warned
  confusingly. Status is now matched by substring (handles both prefixes), and
  the SDK's "not a valid JobState" warning is suppressed.
- **CSV now opens correctly in Excel.** Output CSVs are written as UTF-8 with a
  BOM (`utf-8-sig`) so Excel on Windows shows accented locality names
  (e.g. "Rhône") instead of mojibake ("RhÃ´ne").

## [1.2.4] - 2026-06-06

### Fixed
- **Gemini batch results still failed to parse for some records** ("list indices
  must be integers..."). The parser is now structure-agnostic: it recursively
  finds the answer JSON anywhere in each result line (handling thinking-model
  multi-part responses and any wrapper the batch results file uses) and never
  raises. Failed records now include a `raw_response` snippet to aid diagnosis.
- **Output filename truncated / permission denied.** Model names containing a
  dot (e.g. "Gemini 3.1 Pro") caused `Path.with_suffix()` to truncate
  `..._Gemini_3.1_Pro_..._results` down to `..._Gemini_3.csv`, producing
  colliding names across runs (which surfaced as a Windows "permission denied"
  when a stale file was open). `OutputFormatter` now appends the extension
  instead of using `with_suffix`, preserving the full unique filename.

## [1.2.3] - 2026-06-06

### Fixed
- **Batch download dropped records.** When a Gemini batch result line failed to
  parse, it was only printed and never added to the results, so records went
  missing silently (e.g. 3 of 5 returned) and the failure count read 0. The
  parser now accounts for every record (success or failure with a reason).
- **Thinking-model responses now parse.** Gemini 3.x Pro returns multi-part
  responses (a non-text "thought" part plus the answer); the old parser blindly
  read `parts[0].text` and raised "list indices must be integers...". Text is
  now extracted by scanning all parts, tolerant of `content` being a dict or a
  bare list.
- **Batch download ignored the chosen output format.** It always wrote
  `_results.json` regardless of the CSV/JSON/GeoJSON selection. It now honours
  the formats chosen at submission, merges results back with the source
  dataset's columns (e.g. original locality text), and writes to
  `~/.placebot/output` instead of the install directory.
- **GeoJSON export produced no features.** `OutputFormatter.to_geojson` only
  looked for lowercase `latitude`/`longitude`, but records use `Latitude`/
  `Longitude`, so every feature was skipped. It now accepts both.

## [1.2.2] - 2026-06-06

### Fixed
- The Gemini Pro profile used `gemini-3-pro-preview`, which Google shut down on
  2026-03-09 (404 "model no longer available"). Updated to the current preview
  Pro model **`gemini-3.1-pro-preview`** ("Gemini 3.1 Pro"); profile renamed to
  `gemini_3_1_pro.py`. Added a comment noting Gemini Pro preview IDs rotate
  every few months and where to find the current one.

## [1.2.1] - 2026-06-06

### Fixed
- GPT-5 / GPT-5 mini requests timed out after 30s because GPT-5 is a reasoning
  model and "thinks" before responding. They now send
  `reasoning_effort="minimal"` (deep reasoning isn't needed for locality
  extraction, and it keeps latency/cost low) and use a 120s request timeout via
  a new per-model `REQUEST_TIMEOUT` setting. The OpenAI batch path applies the
  same minimal-reasoning setting and a larger token budget for reasoning models.

## [1.2.0] - 2026-06-06

### Added
- OpenAI **GPT-5** and **GPT-5 mini** model profiles (current generation).

### Changed
- Refreshed OpenAI pricing for GPT-4.1 (~$2/$8 per 1M) and GPT-4.1-mini
  (~$0.40/$1.60 per 1M).
- Replaced the deprecated Gemini 2.5 profiles (shutting down ~June–July 2026)
  with **Gemini 3.5 Flash** (stable) and **Gemini 3 Pro** (preview). Profile
  files renamed to `gemini_3_5_flash.py` and `gemini_3_pro.py`.
- OpenAI batch requests now send `max_completion_tokens` instead of the
  deprecated `max_tokens`, required by GPT-5-class models.
- Updated deprecated fallback model IDs in the batch processors
  (`gpt-4o-mini` → `gpt-4.1-mini`, `gemini-2.0-flash-exp`/`gemini-2.5-flash`
  → `gemini-3.5-flash`).

### Removed
- **o4-mini** profile (retired from ChatGPT; reasoning model not needed for
  locality extraction).
- **Gemini 2.5 Flash-Lite** profile (no Gemini 3 equivalent; lineup
  consolidated).

### Notes
- GPT-5 profiles omit `temperature`/`top_p` — GPT-5-class models reject sampling
  parameters on chat completions. GPT-4.1 retains its classic request shape.
- Model IDs/pricing reflect the best available public information as of
  2026-06-06; verify against each provider's live pricing/models pages.

## [1.1.1] - 2026-06-06

### Fixed
- Updated the Claude model profiles to current model IDs. The previous Haiku
  profile used `claude-3-5-haiku-20241022`, which Anthropic retired on
  2026-02-19 and now returns HTTP 404. The Sonnet/Opus profiles used the
  `claude-*-4-20250514` IDs, which are deprecated and retiring 2026-06-15.
  Profiles now use `claude-haiku-4-5`, `claude-sonnet-4-6`, and
  `claude-opus-4-8`, with refreshed pricing and display names. Model profile
  files were renamed to match (`claude_haiku_4_5.py`, `claude_sonnet_4_6.py`,
  `claude_opus_4_8.py`).
- Removed the `temperature` sampling parameter from the Opus 4.8 request
  builder — Opus 4.8 rejects sampling parameters with a 400 error.
- Replaced retired fallback model IDs (`claude-3-haiku-20240307`,
  `claude-3-5-haiku-20241022`) used as defaults in the real-time and batch
  request paths.

## [1.1.0] - 2026-06-05

### Added
- 🖥️ **Graphical interface** (`placebot-gui`): a lightweight Streamlit app aimed
  at non-technical users — paste an API key, upload a dataset, pick a model,
  run, and download CSV/JSON/GeoJSON results. Install with `pip install "placebot[gui]"`.
- In-app API key management: keys entered in the GUI are saved to
  `~/.placebot/.env` and remembered between sessions.
- `progress_callback` hook on `BatchProcessor.process_dataset()` so front-ends
  can drive a progress bar (backward compatible; CLI unchanged).
- Real `tests/` suite (pytest) and GitHub Actions CI (test matrix + lint).
- GitHub Actions release workflow for publishing to PyPI via Trusted Publishing.

### Changed
- Data directories now live under `~/.placebot/` (input/output/config) instead
  of inside the installed package, so `pip install` works correctly and data
  survives upgrades. Override with the `PLACEBOT_HOME` environment variable.
- API keys are now read from `~/.placebot/.env` in addition to project-level
  `.env` files.

### Fixed
- Added missing `requests` runtime dependency (previously only in
  `requirements.txt`), so `pip install placebot` works out of the box.
- Model cost estimates are no longer always `$0.00` — per-million pricing is now
  derived from each model profile.
- `DatasetPreview.get_statistics()` no longer crashes on ragged CSV rows
  (`None` column names).
- Removed placeholder API keys from the 12 model profile files.
- Corrected the stale `--batch` CLI message and the welcome banner branding.

## [1.0.0] - 2025-10-16

### Added
- 🎉 Initial public release
- Support for 12 AI models across 4 vendors:
  - Anthropic models (3 profiles)
  - OpenAI GPT (3 models)
  - Google Gemini (3 models)
  - Local Qwen (3 models)
- Interactive CLI with user-friendly prompts
- Real-time and batch processing modes
- Advanced caching strategies (up to 90% cost savings)
- Async batch API integration (50% cost discount)
- Multi-API key support for large datasets
- Cost estimation before processing
- Model comparison tool
- Dataset preview functionality
- Multiple output formats (CSV, JSON, GeoJSON)
- Comprehensive error handling and retry logic
- Production-ready performance (tested on 3000+ records)

### Features
- **Processing Modes**:
  - Real-time processing for urgent/small datasets
  - Batch processing for cost optimization
  - Staggered batch processing for rate limit management
  
- **Cost Optimization**:
  - Claude: Explicit prompt caching (90% savings)
  - OpenAI: Automatic prompt caching (50% savings)
  - Gemini: Explicit caching with 1-hour TTL (75% savings)
  - Batch API discounts across all vendors

- **Model Performance**:
  - Speed range: 0.98s - 17.04s per record
  - Accuracy: high benchmark success rates in the original test set
  - Cloud models: strongest benchmark performance in the original test set
  - Local models: strong benchmark performance with no API cost

### Documentation
- Comprehensive README with usage examples
- Contributing guidelines
- Example datasets
- API key setup instructions
- Model comparison guide
- Performance benchmarks

### Developer Experience
- Clean package structure
- Type hints throughout codebase
- Comprehensive error messages
- Detailed logging
- Easy installation with pip

## [Unreleased]

### Planned
- Web interface for browser-based processing
- REST API for system integration
- Docker container for easy deployment
- Additional model vendors (Cohere, Mistral)
- Confidence scoring and uncertainty quantification
- Real-time coordinate validation
- Fine-tuning support for domain-specific data
- Enhanced visualization tools
- Performance monitoring dashboard

---

For older changes, see [GitHub Releases](https://github.com/JackDanHollister/PlaceBot/releases)
