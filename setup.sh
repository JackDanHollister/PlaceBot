#!/bin/bash

# Ben's Locality Processor - Setup Script
# Automated installation and configuration

echo "🚀 Setting up Ben's Locality Processor..."
echo "=========================================="

# Check Python version
python_version=$(python3 --version 2>&1 | cut -d' ' -f2)
echo "✅ Python version: $python_version"

# Install dependencies
echo "📦 Installing Python dependencies..."
pip3 install -r requirements.txt

# Create output directories
echo "📁 Creating output directories..."
mkdir -p output results graphs consistency_analysis

# Set permissions
chmod +x *.py

echo ""
echo "🎉 Setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Add your API keys to model files in models/ directory"
echo "2. Place your data files in input/ directory"
echo "3. Run: python main.py (single model) or python run_combined_analysis.py (full analysis)"
echo ""
echo "📖 For detailed usage instructions, see README.md"
echo ""
echo "🔬 Ready to process museum locality data!"
