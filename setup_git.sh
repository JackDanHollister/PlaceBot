#!/bin/bash

# PlaceBot - GitHub Repository Setup Script
# This script initializes the Git repository and prepares for first push

echo "🚀 PlaceBot GitHub Setup"
echo "========================"
echo ""

# Check if already a git repo
if [ -d ".git" ]; then
    echo "⚠️  Git repository already exists!"
    echo "Do you want to reinitialize? (y/n)"
    read -r response
    if [ "$response" != "y" ]; then
        echo "Exiting..."
        exit 0
    fi
    rm -rf .git
fi

# Initialize git repository
echo "📦 Initializing Git repository..."
git init

# Create main branch
echo "🌿 Creating main branch..."
git branch -M main

# Add all files
echo "➕ Adding files to staging..."
git add .

# Create initial commit
echo "💾 Creating initial commit..."
git commit -m "Initial release: PlaceBot v1.0.0

- 12 AI models across 4 vendors (Claude, OpenAI, Gemini, Qwen)
- Real-time and batch processing modes
- Advanced caching (up to 90% cost savings)
- 10 example datasets included
- Production-ready (tested on 3000+ records)
- Comprehensive documentation
"

# Add remote
echo ""
echo "🔗 Adding GitHub remote..."
git remote add origin https://github.com/JackDanHollister/PlaceBot.git

echo ""
echo "✅ Setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Make sure the GitHub repository exists at:"
echo "   https://github.com/JackDanHollister/PlaceBot"
echo ""
echo "2. Push to GitHub:"
echo "   git push -u origin main"
echo ""
echo "3. Create a release:"
echo "   - Go to: https://github.com/JackDanHollister/PlaceBot/releases"
echo "   - Click 'Create a new release'"
echo "   - Tag: v1.0.0"
echo "   - Title: PlaceBot v1.0.0 - Initial Public Release"
echo "   - Copy description from CHANGELOG.md"
echo ""
echo "🎉 Happy coding!"
