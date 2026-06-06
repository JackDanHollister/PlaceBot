<p align="center">
  <img src="doc/placebot_logo.png" alt="PlaceBot Logo" width="300"/>
</p>

# PlaceBot - Multi-Vendor AI Locality Processor

PlaceBot is a lightweight tool designed to convert verbatim locality descriptions, such as those found on natural history specimen labels, into standardised geographic coordinates (latitude and longitude). It uses modern natural language processing (NLP) and large language model (LLM) techniques to interpret descriptive place names, estimate coordinates, convert grid references, and assess confidence levels.

This tool is intended to support digitisation, curation, and research workflows by automating a key step in georeferencing legacy specimen data.

## Key Features

- **12 AI Models**: Claude (3 models), OpenAI (3 models), Gemini (3 models), Qwen Local (3 models)
- **Cost Optimisation**: Up to 90% savings with advanced caching strategies
- **Batch Processing**: 50% cost reduction using asynchronous batch APIs
- **High Accuracy**: 97-100% success rate on coordinate extraction
- **Privacy Options**: Local Qwen models for offline processing
- **Performance Tracking**: Built-in benchmarking and comparison tools
- **Production Ready**: Tested on 100+ records, scales to thousands

## Quick Start

### Installation

```bash
# From PyPI (recommended) - includes the graphical interface
pip install "placebot[gui]"

# Or, for local Ollama model support
pip install "placebot[local]"
```

<details>
<summary>Install from source (for development)</summary>

```bash
git clone https://github.com/JackDanHollister/PlaceBot.git
cd PlaceBot
pip install -e ".[gui]"
```
</details>

### Graphical interface (easiest)

```bash
placebot-gui
```

This opens PlaceBot in your browser. From the graphical interface you can:

- Paste your API keys in the sidebar (saved to `~/.placebot/.env`), including
  multiple Gemini keys for very large jobs.
- Upload a CSV/TSV file and preview it.
- Pick a model directly from the comparison table.
- Run in real-time, submit a batch job, or use staggered batch for very
  large, quota-safe jobs.
- Download completed batch results (including merged staggered jobs) without
  opening a terminal.
- Results are saved straight to your output folder (CSV uses a UTF-8 BOM so
  Excel shows accents correctly), with one-click access to that folder.

No terminal knowledge is required.

### Command-line usage

```bash
# Run the interactive CLI
placebot

# Or use the short alias
pb
```

The CLI will guide you through:
1. Selecting processing mode (real-time or batch)
2. Choosing your AI model
3. Loading your data file
4. Viewing cost estimates
5. Processing and exporting results

### Configuration (command line)

Add at least one API key to `~/.placebot/.env`:
```env
ANTHROPIC_API_KEY=your_anthropic_key_here
OPENAI_API_KEY=your_openai_key_here
GOOGLE_API_KEY=your_google_key_here
```

Get your API keys from:
- **Anthropic**: https://console.anthropic.com/
- **OpenAI**: https://platform.openai.com/api-keys
- **Google**: https://aistudio.google.com/app/apikey

(The graphical interface writes this file for you.) Run `placebot --show-dirs`
to see where PlaceBot stores input, output, and configuration.

## Input Data Format

PlaceBot accepts TSV or CSV files with locality descriptions:

```tsv
locality_id	locality_description
1	"California, San Francisco Bay, Golden Gate Park"
2	"UK, Scotland, Edinburgh, Royal Botanic Garden"
```

## Model Comparison

PlaceBot ships 12 model profiles across 4 vendors. Speed/accuracy figures are
indicative (measured on earlier model versions); cost is the per-token list
price tier. Verify current pricing with each provider.

| Vendor | Model | Cost | Best For |
|--------|-------|------|----------|
| **Gemini** | Gemini 3.5 Flash | Low | Speed & cost (stable) |
| **Claude** | Haiku 4.5 | Low | Reliability |
| **OpenAI** | GPT-4.1-mini | Very Low | Balance |
| **OpenAI** | GPT-5 mini | Low | Cost-efficient current-gen |
| **Claude** | Sonnet 4.6 | Medium | Premium quality |
| **OpenAI** | GPT-4.1 | Medium | Large context |
| **OpenAI** | GPT-5 | Medium | Highest-quality extraction |
| **Claude** | Opus 4.8 | Medium | Deep reasoning |
| **Gemini** | Gemini 3.1 Pro (preview) | Medium | Advanced tasks |
| **Qwen** | 3 1.7B (local) | **FREE** | Privacy/offline |
| **Qwen** | 3 14B (local) | **FREE** | Best local |
| **Qwen** | 3 8B (local) | **FREE** | Offline balance |

## Advanced Features

### Batch Processing

Process large datasets with 50% cost savings:

```bash
placebot-batch
```

Batch processing is ideal for:
- Museum collections (1000+ specimens)
- Historical archives
- Large biodiversity datasets
- Any dataset where 24-hour processing time is acceptable

For very large datasets (3,000+ records), **staggered batch** mode splits the
job into several smaller sub-batches submitted with short delays, so you stay
under each provider's quota limits while keeping the 50% batch discount.

Batch and staggered jobs submitted from the graphical interface can also be
fetched (and, for staggered jobs, merged) from the **Batch downloads** page
once they complete — no command line required.

### Cost Optimisation

PlaceBot implements multiple cost-saving strategies:

**1. Prompt Caching** (up to 90% savings)
- Claude: Explicit caching with 5-minute TTL
- OpenAI: Automatic caching (50% discount)
- Gemini: Explicit caching with 1-hour TTL

**2. Batch API Processing** (50% discount)
- Available for all 3 cloud vendors
- Asynchronous processing with 24-hour completion
- Automatic retry and error handling

**3. Smart Model Selection**
- Cost estimator shows price before processing
- Model comparison tool helps choose the optimal model
- Local models available for zero API costs

### Multi-API Key Support

For processing very large datasets, you can configure multiple Gemini API keys:

```env
GOOGLE_API_KEY=your_primary_key
GOOGLE_API_KEY_2=your_secondary_key
GOOGLE_API_KEY_3=your_tertiary_key
```

These can be entered directly in the graphical interface (under the Google
section of the sidebar) or added to `~/.placebot/.env` by hand. Additional keys
let you spread very large jobs across separate Gemini quotas.

## Output Formats

Choose from multiple output formats:

- **CSV**: Standard comma-separated values
- **JSON**: Machine-readable structured data
- **GeoJSON**: Geographic data format for GIS tools

Example output:
```json
{
  "locality_id": "1",
  "original_locality": "California, San Francisco Bay, Golden Gate Park",
  "extracted_coordinates": {
    "latitude": 37.7694,
    "longitude": -122.4862
  },
  "confidence": "high",
  "model_used": "claude-3.5-haiku",
  "processing_time": 7.2
}
```

## Development

### Project Structure

```
placebot/
├── placebot/              # Main package
│   ├── cli/              # Command-line interface
│   │   ├── main.py       # Main CLI entry point
│   │   ├── batch_manager.py  # Batch processing manager
│   │   └── user_interface.py # Interactive prompts
│   ├── core/             # Core processing modules
│   │   ├── ai_processor.py      # AI model integration
│   │   ├── batch_processor.py   # Asynchronous batch processing
│   │   ├── async_batch_processor.py  # Advanced batch logic
│   │   ├── config.py            # API key management
│   │   ├── cost_estimator.py    # Cost calculations
│   │   ├── dataset_preview.py   # Data preview
│   │   ├── model_comparison.py  # Model comparison
│   │   ├── output_formatter.py  # Export formats
│   │   ├── coordinate_utils.py  # Coordinate validation
│   │   └── file_manager.py      # File I/O operations
│   ├── gui/              # Streamlit graphical interface
│   └── models/           # AI model implementations
│       ├── claude_*.py   # Claude model configs
│       ├── gpt_*.py      # OpenAI model configs
│       ├── gemini_*.py   # Gemini model configs
│       └── qwen*.py      # Local Qwen configs
├── pyproject.toml        # Package configuration
├── requirements.txt      # Python dependencies
└── README.md            # This file
```

### Running Tests

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/

# Run with coverage
pytest --cov=placebot tests/
```

## Performance Metrics

Based on testing with 100+ records:

### Speed Comparison
- **Fastest**: Gemini 2.5 Flash-Lite (0.98s average)
- **Cloud Average**: 3-14 seconds per record
- **Local Average**: 10-17 seconds per record

### Accuracy
- **Cloud Models**: 100% success rate
- **Local Models**: 97-100% success rate

### Cost Efficiency
- **Without Caching**: $0.50-2.00 per 1000 records
- **With Caching**: $0.05-0.20 per 1000 records (90% savings)
- **Batch Processing**: Additional 50% discount
- **Local Models**: $0 (free)

## Architecture

PlaceBot uses a modular architecture:

1. **CLI Layer**: User interaction and input validation
2. **Processing Layer**: AI model orchestration and coordination
3. **Model Layer**: Individual model implementations
4. **Caching Layer**: Prompt caching and optimisation
5. **Output Layer**: Result formatting and export

### Caching Strategy

Each vendor has different caching capabilities:

**Claude (Anthropic)**:
- Manual cache control with `cache_control` parameter
- 5-minute TTL
- Requires 1024+ tokens for caching
- Best for: High-volume processing with identical prompts

**OpenAI**:
- Automatic prompt caching
- 5-10 minute TTL
- No configuration required
- Best for: Simple integration, automatic optimisation

**Gemini (Google)**:
- Explicit caching with `cached_content` API
- 1-hour default TTL (customisable)
- Requires 1024-2048+ tokens depending on model
- Best for: Long-running batch jobs

## Use Cases

PlaceBot is ideal for:

- **Natural History Museums**: Processing specimen locality data
- **Biodiversity Research**: Geocoding occurrence records
- **Historical Archives**: Extracting coordinates from historical documents
- **Field Research**: Converting field notes to coordinates
- **Data Migration**: Bulk processing of legacy locality data

## Citation

If you use PlaceBot in your research, please cite:

```bibtex
@software{placebot2025,
  title = {PlaceBot: Multi-Vendor AI Locality Processor},
  author = {Jack Hollister and Ben Price and {Anthropic Claude}},
  year = {2025},
  url = {https://github.com/JackDanHollister/PlaceBot}
}
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

Made for the biodiversity and research community.
</content>
</invoke>
