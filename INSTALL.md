# Installation Guide

## Quick Start (5 minutes)

### 1. Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- API keys from AI providers (see step 3)

Check your Python version:
```bash
python --version  # Should be 3.8+
```

### 2. Install PlaceBot

**Option A — One-click installer (no Python required, easiest for most staff)**

If you just want to click an icon and go, download a pre-built installer from the
[**Releases page**](https://github.com/JackDanHollister/PlaceBot/releases):

| Platform | Download | How to install |
|----------|----------|----------------|
| **Windows** | `PlaceBot-Setup-<version>.exe` | Double-click, follow the prompts. A **PlaceBot** icon is added to your Desktop and Start Menu. |
| **macOS** | `PlaceBot-<version>.dmg` | Double-click, drag **PlaceBot** into Applications. Launch from Launchpad/Spotlight. |

These bundle their own Python, so you do **not** need Python installed. Then open
PlaceBot from its desktop icon and skip straight to step 3 (API keys).

> First launch on an **unsigned** build: Windows may show a SmartScreen warning
> (click *More info → Run anyway*); on macOS, **right-click the app → Open** the
> first time (or run `xattr -dr com.apple.quarantine /Applications/PlaceBot.app`).
> Code signing is on the roadmap to remove these prompts.

**Option B — Install from PyPI (recommended for technical users)**
```bash
# pipx keeps PlaceBot isolated from your other Python tools
pipx install placebot          # or:  pip install placebot

# With the graphical interface:
pipx install "placebot[gui]"   # or:  pip install "placebot[gui]"
```

**Option C — Install from source (for development)**
```bash
# Clone the repository
git clone https://github.com/JackDanHollister/PlaceBot.git
cd PlaceBot

# Install the package (add extras as needed)
pip install -e ".[gui]"        # graphical interface
pip install -e ".[local]"      # local Ollama model support
```

### 3. Get API Keys

You'll need at least ONE API key from these providers:

| Provider | Get Key From | Free Tier | Best For |
|----------|-------------|-----------|----------|
| **Anthropic** | [console.anthropic.com](https://console.anthropic.com/) | $5 credit | Reliability |
| **OpenAI** | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) | $5 credit | Balance |
| **Google** | [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey) | Free tier | Cost & Speed |

**Recommendation**: Start with Google Gemini (free tier) for testing.

### 4. Configure API Keys

**Easiest:** launch the graphical interface (`placebot-gui`) and paste your
key(s) into the sidebar — they are saved to `~/.placebot/.env` automatically
and remembered between sessions. See [Graphical Interface](#graphical-interface-easiest)
below.

**Manual:** create `~/.placebot/.env` with your key(s):

```bash
mkdir -p ~/.placebot
nano ~/.placebot/.env   # or use your preferred editor
```

Example `~/.placebot/.env` file:
```env
# Add at least one API key
ANTHROPIC_API_KEY=sk-ant-your-key-here
OPENAI_API_KEY=sk-proj-your-key-here
GOOGLE_API_KEY=your-google-key-here
```

### 5. Verify Installation

```bash
# Check PlaceBot is installed
placebot --version

# Should output: placebot <version>  (e.g. placebot 1.2.5)
```

### 6. Test with Sample Data

```bash
# Run PlaceBot
placebot

# When prompted:
# 1. Choose "Real-time" mode
# 2. Select any available model
# 3. Use the example file: examples/sample_localities.tsv
# 4. Review cost estimate
# 5. Confirm processing
```

Expected output:
```
✓ Processed 10 records
✓ 100% success rate
✓ Results saved to output/
```

## Graphical Interface (easiest)

If you installed the `gui` extra (`pip install "placebot[gui]"`), you can use
the point-and-click interface instead of the command line:

```bash
placebot-gui
```

This opens PlaceBot in your web browser. From there you can:

1. **Paste your API key** in the sidebar (saved to `~/.placebot/.env`).
2. **Upload** a CSV/TSV file of localities (or pick one already in your input folder).
3. **Choose** a processing mode and AI model — costs are shown up front.
4. **Run** and watch the progress bar.
5. **Download** your results as CSV, JSON, or GeoJSON.

No terminal knowledge required after the one-time install.

## Where PlaceBot stores your data

PlaceBot keeps its files in your home directory so they survive upgrades:

| Folder | Purpose |
|--------|---------|
| `~/.placebot/input/`  | Datasets to process |
| `~/.placebot/output/` | Results |
| `~/.placebot/.env`    | Your saved API keys |

Run `placebot --show-dirs` to see the exact paths. Set the `PLACEBOT_HOME`
environment variable to use a different location.

## Troubleshooting

### "Command not found: placebot"

Try reinstalling:
```bash
pip uninstall placebot
pip install -e .
```

Or use Python module syntax:
```bash
python -m placebot.cli.main
```

### "No API key found"

1. Verify `.env` file exists in project root
2. Check API key format (should start with correct prefix)
3. Restart your terminal after editing `.env`

### "Rate limit exceeded"

- Switch to batch mode for large datasets
- Use multiple API keys (see Advanced Setup)
- Wait a few minutes and retry

### Import Errors

Reinstall dependencies:
```bash
pip install -r requirements.txt
```

## Advanced Setup

### Using Virtual Environments (Recommended)

```bash
# Create virtual environment
python -m venv venv

# Activate it
source venv/bin/activate  # On macOS/Linux
venv\Scripts\activate     # On Windows

# Install PlaceBot
pip install -e .
```

### Development Installation

```bash
# Install with all development dependencies
pip install -e ".[dev,local]"

# Run tests
pytest tests/
```

### Multiple API Keys for Large Datasets

For processing 1000+ records, add multiple Gemini keys:

```env
GOOGLE_API_KEY=your-primary-key
GOOGLE_API_KEY_2=your-secondary-key
GOOGLE_API_KEY_3=your-tertiary-key
GOOGLE_API_KEY_4=your-fourth-key
```

PlaceBot will automatically distribute load across available keys.

### Local Models (Offline Processing)

Install Ollama for local processing:

1. Install Ollama: [ollama.com/download](https://ollama.com/download)
2. Pull Qwen models:
```bash
ollama pull qwen3:1.7b
ollama pull qwen3:8b
ollama pull qwen3:14b
```
3. Install PlaceBot with local support:
```bash
pip install -e ".[local]"
```

## Platform-Specific Notes

### macOS

Should work out of the box with system Python or Homebrew Python.

### Linux

May need to install Python development headers:
```bash
# Ubuntu/Debian
sudo apt-get install python3-dev

# Fedora
sudo dnf install python3-devel
```

### Windows

Use PowerShell or Windows Terminal:
```powershell
# Activate virtual environment
venv\Scripts\activate

# Run PlaceBot
placebot
```

## Next Steps

- Read the [README](README.md) for usage guide
- Try the [examples](examples/) directory
- Check [CONTRIBUTING](CONTRIBUTING.md) for development setup
- Join discussions for help and tips

## Getting Help

- **Issues**: [GitHub Issues](https://github.com/JackDanHollister/PlaceBot/issues)
- **Questions**: [GitHub Discussions](https://github.com/JackDanHollister/PlaceBot/discussions)
- **Email**: jack.d.hollister@gmail.com
