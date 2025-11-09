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

__all__ = [
    "AIProcessor",
    "BatchProcessor",
]


def __getattr__(name):
    """
    Lazy import to avoid import errors when running CLI scripts.
    
    This allows CLI scripts like batch_status and batch_download to run
    via 'python -m placebot.cli.batch_status' without triggering import
    errors from the package __init__.py.
    """
    if name == "AIProcessor":
        from placebot.core.ai_processor import AIProcessor
        return AIProcessor
    elif name == "BatchProcessor":
        from placebot.core.batch_processor import BatchProcessor
        return BatchProcessor
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
