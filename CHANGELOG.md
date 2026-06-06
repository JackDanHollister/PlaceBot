# Changelog

All notable changes to PlaceBot will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
  - Anthropic Claude (3 models)
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
  - Accuracy: 97-100% success rate
  - Cloud models: 100% success rate
  - Local models: 97-100% success rate (FREE)

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
