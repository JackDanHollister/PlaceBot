<p align="center">
  <img src="placebot/gui/placebot_logo.png" alt="PlaceBot Logo" width="300"/>
</p>

# PlaceBot - Multi-Vendor AI Locality Processor

> GBIF challenge branch: this version adds a Darwin Core/GBIF preparation
> command and submission notes. See [`GBIF_CHALLENGE.md`](GBIF_CHALLENGE.md).

PlaceBot is a lightweight tool designed to convert verbatim locality descriptions, such as those found on natural history specimen labels, into standardised geographic coordinates (latitude and longitude). It uses modern natural language processing (NLP) and large language model (LLM) techniques to interpret descriptive place names, estimate coordinates, convert grid references, and assess confidence levels.

This tool is intended to support digitisation, curation, and research workflows by automating a key step in georeferencing legacy specimen data.

## Key Features

- **Multi-vendor AI models**: native Claude, OpenAI, Gemini, local Ollama/Qwen,
  and OpenRouter routes from one key
- **Cost Optimisation**: Up to 90% savings with advanced caching strategies
- **Batch Processing**: 50% cost reduction using asynchronous batch APIs
- **Benchmark Tracking**: Historical test runs record model success rates and
  processing costs for comparison
- **Supplementary Benchmarks**: Public Bombus and Odonata reference datasets
  from the paper analyses are included under `benchmarks/`
- **GBIF/DwC Preparation**: `placebot-gbif-prep` filters GBIF or Darwin Core
  occurrence downloads to records that need candidate georeferences
- **Privacy Options**: Local models via Ollama for offline processing
- **Performance Tracking**: Built-in benchmarking and comparison tools
- **Production Ready**: Tested on 100+ records, scales to thousands

## Quick Start

### Installation

**Current public install route:** install from this GitHub repository with
Python 3.8+:

```bash
git clone https://github.com/JackDanHollister/PlaceBot.git
cd PlaceBot

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # macOS/Linux
# .venv\Scripts\activate         # Windows PowerShell

# GUI install
pip install -e ".[gui]"

# Or include local Ollama support too
pip install -e ".[gui,local]"
```

Then run:

```bash
placebot-gui
```

Pre-built Windows/macOS installers are built by the release workflow and may be
attached to tagged GitHub releases. They are unsigned, so first launch can show
the normal Windows SmartScreen or macOS Gatekeeper warning. PyPI publishing is
configured through Trusted Publishing, but use the GitHub/source install above
until the first public PyPI release is confirmed.

### Graphical interface (easiest)

```bash
placebot-gui
```

This opens PlaceBot in your browser. From the graphical interface you can:

- Use the top **How to use** button for step-by-step workflow instructions.
- Paste your API keys in the sidebar, including multiple Gemini keys for very
  large jobs. Keys are session-only by default; tick **Remember on this
  computer** if you want PlaceBot to save them locally in `~/.placebot/.env`.
- Upload a CSV/TSV file and preview it.
- Pick a model from the comparison table or choose a local Ollama model from
  the local picker.
- Run in real-time, submit a batch job, or use staggered batch for very
  large, quota-safe jobs.
- Download completed batch results (including merged staggered jobs) without
  opening a terminal.
- Results are saved straight to your output folder (CSV uses a UTF-8 BOM so
  Excel shows accents correctly), with one-click access to that folder.

After the one-time install, the graphical workflow does not require terminal
use.

### Command-line usage

```bash
# Run the interactive CLI
placebot

# Or use the short alias
pb
```

For GBIF/Darwin Core occurrence downloads, prepare candidate records first:

```bash
placebot-gbif-prep path/to/gbif_occurrence.csv \
  --output ~/.placebot/input/gbif_placebot_candidates.tsv
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
OPENROUTER_API_KEY=your_openrouter_key_here
```

Get your API keys from:
- **Anthropic**: https://console.anthropic.com/
- **OpenAI**: https://platform.openai.com/api-keys
- **Google**: https://aistudio.google.com/app/apikey
- **OpenRouter**: https://openrouter.ai/keys

The graphical interface can use pasted keys without saving them. If you tick
**Remember on this computer**, it writes the key to `~/.placebot/.env`. Run
`placebot --show-dirs` to see where PlaceBot stores input, output, and
configuration.

## Input Data Format

PlaceBot accepts TSV or CSV files with locality descriptions. It needs a
record identifier column and a locality text column; a country column and
existing coordinates are optional but improve results.

```tsv
Barcode	Locality verbatim	Country
1	"California, San Francisco Bay, Golden Gate Park"	United States
2	"UK, Scotland, Edinburgh, Royal Botanic Garden"	United Kingdom
```

### Darwin Core support

PlaceBot also recognises [Darwin Core](https://dwc.tdwg.org/terms/) column
names, so files exported from collection management systems work without
renaming anything. The following terms are accepted as inputs:

| Concept | Native column | Darwin Core terms accepted |
| --- | --- | --- |
| Record identifier | `Barcode` | `collectionID`, `catalogNumber`, `occurrenceID`, `materialEntityID`, `recordNumber` |
| Locality text | `Locality verbatim` | `verbatimLocality`, `locality` |
| Country | `Country` | `country` |
| Existing coordinates | `Latitude` / `Longitude` | `decimalLatitude` / `decimalLongitude` |
| Verbatim coordinates | — | `verbatimCoordinates`, `verbatimLatitude`, `verbatimLongitude` (passed to the model as context) |

To emit Darwin Core column names in the results, tick **Use Darwin Core (DwC)
output terms** in the GUI, or answer yes at the Darwin Core prompt in the CLI.
PlaceBot's produced columns are then renamed to their closest DwC equivalents
(e.g. `Latitude` → `decimalLatitude`, `Exact_Site` → `locality`,
`Coordinate_Radius_Meters` → `coordinateUncertaintyInMeters`) in every export.

## Benchmark Datasets

Supplementary benchmark files for the paper analyses are included in
[`benchmarks/`](benchmarks/):

| File | Records | Purpose |
| --- | ---: | --- |
| `benchmarks/data/bombus_uk_reference.tsv` | 709 | Bombus locality benchmark input with manual reference coordinates. |
| `benchmarks/data/odonata_global_reference.tsv` | 908 | Odonata locality benchmark input with manual reference coordinates. |
| `benchmarks/results/bombus_uk_model_comparison.tsv` | 709 | Archived multi-model comparison output for the Bombus benchmark. |
| `benchmarks/results/odonata_global_model_comparison.tsv` | 908 | Archived multi-model comparison output for the Odonata benchmark. |

Use the files under `benchmarks/data/` to re-run PlaceBot. The files under
`benchmarks/results/` are paper-era comparison outputs for review and
reproducibility checks.

## Model Comparison

PlaceBot ships native model profiles for Claude, OpenAI, Gemini, and local
Ollama/Qwen models, plus OpenRouter profiles that can route to several vendors
through one key. Speed/accuracy figures are indicative (measured on earlier
model versions); cost is the per-token list price tier. Verify current pricing
with each provider.

For local processing, PlaceBot currently uses [Ollama](https://ollama.com/) to
host and run models on your own machine. Ollama is not the only local model
runner available, but it gives PlaceBot a simple, cross-platform way to discover
installed models and call them from the same workflow as cloud models. The model
profile system is modular, so other local backends can be added later.

In the GUI, the sidebar shows **Local models (Ollama)** on every page. It lists
installed local models when Ollama is running, or gives the install/pull command
if setup is still needed. After choosing a dataset, use **Model source → Local
Ollama** to select one of the local models for processing.

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
| **OpenRouter** | GPT-5 mini, GPT-4.1, Gemini 3.5 Flash, Claude Haiku/Sonnet/Opus | Varies | One-key multi-vendor routing |

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

### Ensemble Analysis

Run the same dataset through two different models, then compare their
coordinate estimates to find where they agree (likely accurate) and where they
diverge (worth a manual check):

```bash
placebot-ensemble
```

You pick which of the two output files is the **primary** (its values are
carried forward), and PlaceBot matches records on their `Barcode`, computes the
great-circle (haversine) distance between the two estimates, and tags each
record with an agreement category:

| Category | Distance between estimates |
|----------|----------------------------|
| close (<2km)    | < 2 km |
| moderate (2-5km) | 2–5 km |
| low (5-10km)    | 5–10 km |
| none (>10km)    | > 10 km |
| no comparison   | coordinates missing in either file, or barcode only in one file |

The output TSV and CSV files contain the carried-forward records plus
`Agreement_Category`, `Distance_km`, and the other model's
`Secondary_Latitude`/`Secondary_Longitude` for reference, so you can filter
straight to the records that need verifying. A summary report shows how many
records fall into each category.

The same workflow is available in the graphical interface on the **Ensemble
analysis** page — just pick the two files from your output folder (or upload
them) and click *Run comparison*.

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
- **TSV**: Tab-separated values, useful for locality text with commas
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
  "model_used": "claude-haiku-4-5",
  "processing_time": 7.2
}
```

## Development

### Project Structure

```
placebot/
├── benchmarks/           # Paper benchmark input and comparison data
├── GBIF_CHALLENGE.md     # GBIF challenge workflow and submission framing
├── placebot/              # Main package
│   ├── cli/              # Command-line interface
│   │   ├── main.py       # Main CLI entry point
│   │   ├── gbif.py       # GBIF/Darwin Core preparation workflow
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

Based on historical testing with 100+ records. These figures are benchmark
context, not a guarantee for every dataset, model version, or provider account.

### Speed Comparison
- **Fastest cloud tier**: Gemini Flash-class models
- **Cloud Average**: typically a few seconds per record, depending on provider
- **Local Average**: hardware-dependent; larger Ollama models are slower but private

### Accuracy
- **Cloud Models**: high success rates in the historical benchmark runs
- **Local Models**: strong local benchmark results, with performance depending
  on the installed model and local hardware

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
  author = {Jack Hollister and Ben Price},
  year = {2026},
  url = {https://github.com/JackDanHollister/PlaceBot}
}
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

Made for the biodiversity and research community.
