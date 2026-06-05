# Changelog

All notable changes to PlaceBot will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
