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

**Option A — Install from GitHub/source (current public route)**

```bash
# Clone the repository
git clone https://github.com/JackDanHollister/PlaceBot.git
cd PlaceBot

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # macOS/Linux
# .venv\Scripts\activate         # Windows PowerShell

# Install the graphical interface
pip install -e ".[gui]"

# Or include local Ollama model support too
pip install -e ".[gui,local]"
```

**Option B — One-click installers and PyPI**

The repository includes release tooling for Windows/macOS installers and PyPI
publishing. Tagged GitHub releases may have unsigned installer assets attached;
PyPI publishing is configured through Trusted Publishing, but use Option A until
the first public PyPI release is confirmed.

When installer assets are published, they are expected to be named
`PlaceBot-Setup-<version>.exe` for Windows and `PlaceBot-<version>.dmg` for
macOS. Windows installers add Desktop/Start Menu shortcuts; macOS installers
provide a `PlaceBot.app` bundle to drag into Applications.

### 3. Get API Keys

You'll need at least ONE API key from these providers:

| Provider | Get Key From | Free Tier | Best For |
|----------|-------------|-----------|----------|
| **Anthropic** | [console.anthropic.com](https://console.anthropic.com/) | $5 credit | Reliability |
| **OpenAI** | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) | $5 credit | Balance |
| **Google** | [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey) | Free tier | Cost & Speed |
| **OpenRouter** | [openrouter.ai/keys](https://openrouter.ai/keys) | Varies | One key for multiple vendors |

**Recommendation**: Start with Google Gemini (free tier) for testing.

### 4. Configure API Keys

**Easiest:** launch the graphical interface (`placebot-gui`) and paste your
key(s) into the sidebar. They are used for the current GUI session by default.
Tick **Remember on this computer** only if you want PlaceBot to save them to
`~/.placebot/.env` for future sessions. See
[Graphical Interface](#graphical-interface-easiest) below.

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
OPENROUTER_API_KEY=sk-or-your-key-here
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
# 3. Use the example file: examples/ai_test.tsv
# 4. Review cost estimate
# 5. Confirm processing
```

Successful runs write output files and report the processed record count:
```
Processed 4 records
Results saved to output/
```

## Graphical Interface (easiest)

If you installed the `gui` extra (`pip install -e ".[gui]"`), you can use
the point-and-click interface instead of the command line:

```bash
placebot-gui
```

This opens PlaceBot in your web browser. From there you can:

1. **Paste your API key** in the sidebar. It is session-only unless you tick
   **Remember on this computer**.
2. **Upload** a CSV/TSV file of localities (or pick one already in your input folder).
3. **Choose** a processing mode and AI model — costs are shown up front. For
   local models, check **Local models (Ollama)** in the sidebar.
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
pip install -e ".[gui]"
```

Or use Python module syntax:
```bash
python -m placebot.cli.main
```

### "No API key found"

1. Verify `~/.placebot/.env` exists, or paste the key into the GUI sidebar
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
pip install -e ".[gui]"
```

### Development Installation

```bash
# Install with all development dependencies
pip install -e ".[dev,gui,local]"

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
pip install -e ".[gui,local]"
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
