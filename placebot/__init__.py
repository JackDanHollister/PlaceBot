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

try:
    from importlib.metadata import PackageNotFoundError, version as _pkg_version
    try:
        __version__ = _pkg_version("placebot")
    except PackageNotFoundError:  # running from a source tree without install
        __version__ = "0.0.0+unknown"
except ImportError:  # Python < 3.8 (defensive; project targets >=3.8)
    __version__ = "0.0.0+unknown"

__author__ = "Jack Hollister"
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
