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

```bash
# Clone the repository
git clone https://github.com/yourusername/placebot.git
cd placebot

# Install the package
pip install -e .
```

**Optional: Install with local model support**
```bash
pip install -e ".[local]"
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

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and add your API key(s)
nano .env  # or use your preferred editor
```

Example `.env` file:
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

# Should output: placebot 1.0.0
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
ollama pull qwen2.5:1.5b
ollama pull qwen2.5:7b
ollama pull qwen2.5:14b
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

- **Issues**: [GitHub Issues](https://github.com/yourusername/placebot/issues)
- **Questions**: [GitHub Discussions](https://github.com/yourusername/placebot/discussions)
- **Email**: your.email@example.com
