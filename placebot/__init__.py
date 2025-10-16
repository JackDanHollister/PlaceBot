"""
PlaceBot
========

Multi-vendor AI locality processor for extracting geographic coordinates 
from locality descriptions using 12 AI models across 4 vendors.

Supports:
- Claude (Anthropic): 3 models
- OpenAI: 3 models  
- Gemini (Google): 3 models
- Qwen (Local via Ollama): 3 models

Features:
- Real-time and batch processing modes
- Advanced caching (50-90% cost savings)
- Multiple output formats (CSV, JSON, GeoJSON)
- Cost estimation and model comparison
"""

__version__ = "1.0.0"
__author__ = "Your Name"
__license__ = "MIT"

from placebot.core.ai_processor import AIProcessor
from placebot.core.batch_processor import BatchProcessor

__all__ = [
    "AIProcessor",
    "BatchProcessor",
]
