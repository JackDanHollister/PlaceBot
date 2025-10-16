# Changelog

All notable changes to PlaceBot will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
