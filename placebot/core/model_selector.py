#!/usr/bin/env python3
"""
Model Selection Utility
=======================

Handles loading and selecting AI models from profile files.
Each model has its own configuration file with API keys, pricing, and capabilities.
"""

import os
import importlib.util
from typing import Dict, List, Optional, Any
import sys
from types import SimpleNamespace

import requests


OLLAMA_API_ENDPOINT = "http://localhost:11434/api/generate"
OLLAMA_TAGS_ENDPOINT = "http://localhost:11434/api/tags"
OLLAMA_DYNAMIC_PREFIX = "ollama:"


def is_local_model_config(model_config: Dict[str, Any]) -> bool:
    """Return True for local/Ollama-backed model configs."""
    name = str(model_config.get("name", "")).lower()
    provider = str(model_config.get("provider", "")).lower()
    endpoint = str(model_config.get("api_endpoint", "")).lower()
    return (
        model_config.get("type") == "local"
        or "ollama" in provider
        or "qwen" in name
        or "localhost:11434" in endpoint
    )


def get_ollama_models(timeout: float = 0.5) -> List[Dict[str, Any]]:
    """Return locally installed Ollama models, or [] if Ollama is unavailable."""
    try:
        response = requests.get(OLLAMA_TAGS_ENDPOINT, timeout=timeout)
        response.raise_for_status()
        models = response.json().get("models", [])
    except Exception:
        return []

    installed = []
    for model in models:
        name = model.get("model") or model.get("name")
        if not name:
            continue
        installed.append(
            {
                "name": name,
                "size": model.get("size"),
                "details": model.get("details", {}),
                "modified_at": model.get("modified_at", ""),
            }
        )
    return installed


def _format_ollama_request(model_id: str, prompt: str, max_tokens: int = 8192) -> dict:
    """Format a request for Ollama's /api/generate endpoint."""
    return {
        "model": model_id,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "top_p": 0.8,
            "num_ctx": 8192,
            "num_predict": min(max_tokens, 8192),
        },
    }


def _make_ollama_module(model_id: str) -> SimpleNamespace:
    """Build a small module-like adapter for dynamically discovered Ollama models."""
    return SimpleNamespace(
        get_headers=lambda api_key=None: {"Content-Type": "application/json"},
        format_request=lambda prompt, max_tokens=8192, cached_content_name=None: (
            _format_ollama_request(model_id, prompt, max_tokens)
        ),
        parse_response=lambda response_json: response_json["response"],
    )


def _ollama_profile_from_model(model_info: Dict[str, Any]) -> Dict[str, Any]:
    """Create a runnable model profile from an installed Ollama model."""
    model_id = model_info["name"]
    details = model_info.get("details") or {}
    family = details.get("family") or "local"
    parameters = details.get("parameter_size") or "unknown size"
    quant = details.get("quantization_level") or "unknown quantization"
    return {
        "name": f"Ollama: {model_id} (Local)",
        "provider": "Local (Ollama)",
        "model_id": model_id,
        "api_endpoint": OLLAMA_API_ENDPOINT,
        "api_key": None,
        "cost_per_1k_input": 0,
        "cost_per_1k_output": 0,
        "input_cost_per_million": 0,
        "output_cost_per_million": 0,
        "type": "local",
        "estimated_cost_per_record": 0,
        "max_tokens": 8192,
        "max_output_tokens": 8192,
        "requests_per_minute": 999999,
        "request_timeout": 120,
        "speed": "Local hardware dependent",
        "accuracy": f"{parameters} {family}",
        "cost_efficiency": "Perfect (Free)",
        "best_for": "Installed local Ollama model",
        "local_ready": True,
        "local_status": "Installed",
        "local_status_detail": f"{parameters}, {quant}",
        "get_headers": None,
        "format_request": None,
        "parse_response": None,
        "module": _make_ollama_module(model_id),
    }


def _apply_ollama_runtime_status(profile: Dict[str, Any]) -> Dict[str, Any]:
    """Annotate a local profile with whether its Ollama model is installed."""
    if not is_local_model_config(profile):
        return profile

    installed = get_ollama_models()
    installed_ids = {m["name"] for m in installed}
    model_id = profile.get("model_id", "")
    if model_id in installed_ids:
        profile["local_ready"] = True
        profile["local_status"] = "Installed"
        profile["local_status_detail"] = model_id
    elif installed:
        profile["local_ready"] = False
        profile["local_status"] = "Model not installed"
        profile["local_status_detail"] = f"Run: ollama pull {model_id}"
    else:
        profile["local_ready"] = False
        profile["local_status"] = "Ollama unavailable or no models installed"
        profile["local_status_detail"] = "Start Ollama or install a model"
    return profile


def discover_models() -> List[str]:
    """Discover available model profile files in the models/ directory."""
    # Get the directory containing this script, then go up one level to find models/
    current_dir = os.path.dirname(os.path.abspath(__file__))
    models_dir = os.path.join(os.path.dirname(current_dir), "models")

    if not os.path.exists(models_dir):
        return []

    model_files = []
    for filename in os.listdir(models_dir):
        if filename.endswith(".py") and not filename.startswith("__"):
            model_name = filename[:-3]  # Remove .py extension
            model_files.append(model_name)

    return sorted(model_files)


def load_model_profile(model_file: str) -> Optional[Dict[str, Any]]:
    """Load a model profile from a .py file."""
    try:
        if model_file.startswith(OLLAMA_DYNAMIC_PREFIX):
            model_id = model_file[len(OLLAMA_DYNAMIC_PREFIX) :]
            for installed in get_ollama_models():
                if installed["name"] == model_id:
                    return _ollama_profile_from_model(installed)
            return None

        # Get the directory containing this script, then go up one level to find models/
        current_dir = os.path.dirname(os.path.abspath(__file__))
        models_dir = os.path.join(os.path.dirname(current_dir), "models")
        file_path = os.path.join(models_dir, f"{model_file}.py")

        if not os.path.exists(file_path):
            return None

        # Load the module dynamically
        spec = importlib.util.spec_from_file_location(model_file, file_path)
        if spec is None or spec.loader is None:
            return None

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Import config to get API keys from .env file
        from placebot.core.config import get_config

        config = get_config()

        # Get provider and determine which API key to use
        provider = getattr(module, "MODEL_PROVIDER", "Unknown").lower()

        # Get API key from .env file first, fall back to hardcoded value
        env_api_key = None
        if "anthropic" in provider or "claude" in provider:
            env_api_key = config.get_api_key("anthropic")
        elif "openai" in provider or "gpt" in provider:
            env_api_key = config.get_api_key("openai")
        elif "google" in provider or "gemini" in provider:
            env_api_key = config.get_api_key("google")
        elif "openrouter" in provider:
            env_api_key = config.get_api_key("openrouter")

        # Use environment API key if available, otherwise use hardcoded value from model file
        api_key = env_api_key if env_api_key else getattr(module, "API_KEY", "")

        # Extract model information
        profile = {
            "name": getattr(module, "MODEL_NAME", model_file),
            "provider": getattr(module, "MODEL_PROVIDER", "Unknown"),
            "model_id": getattr(module, "MODEL_ID", ""),
            "api_endpoint": getattr(module, "API_ENDPOINT", ""),
            "api_key": api_key,
            "cost_per_1k_input": getattr(module, "COST_PER_1K_INPUT_TOKENS", 0),
            "cost_per_1k_output": getattr(module, "COST_PER_1K_OUTPUT_TOKENS", 0),
            # Per-million pricing consumed by CostEstimator (1k * 1000)
            "input_cost_per_million": getattr(module, "COST_PER_1K_INPUT_TOKENS", 0)
            * 1000,
            "output_cost_per_million": getattr(module, "COST_PER_1K_OUTPUT_TOKENS", 0)
            * 1000,
            "type": (
                "local"
                if "ollama" in str(getattr(module, "MODEL_PROVIDER", "")).lower()
                or "qwen" in str(getattr(module, "MODEL_NAME", "")).lower()
                else "cloud"
            ),
            "estimated_cost_per_record": getattr(
                module, "ESTIMATED_COST_PER_RECORD", 0
            ),
            "max_tokens": getattr(module, "MAX_TOKENS", 4096),
            "max_output_tokens": getattr(module, "MAX_OUTPUT_TOKENS", 2000),
            "requests_per_minute": getattr(module, "REQUESTS_PER_MINUTE", 50),
            "request_timeout": getattr(module, "REQUEST_TIMEOUT", 30),
            "speed": getattr(module, "SPEED", "Unknown"),
            "accuracy": getattr(module, "ACCURACY", "Unknown"),
            "cost_efficiency": getattr(module, "COST_EFFICIENCY", "Unknown"),
            "best_for": getattr(module, "BEST_FOR", ""),
            "get_headers": getattr(module, "get_headers", None),
            "format_request": getattr(module, "format_request", None),
            "parse_response": getattr(module, "parse_response", None),
            "module": module,  # Keep reference to the module
        }

        _apply_ollama_runtime_status(profile)
        return profile

    except Exception as e:
        print(f"Error loading model profile {model_file}: {e}")
        return None


def load_all_model_profiles(
    include_dynamic_ollama: bool = False,
) -> List[Dict[str, Any]]:
    """Load static model profiles and, optionally, installed Ollama models."""
    profiles = []
    static_model_ids = set()

    for model_file in discover_models():
        profile = load_model_profile(model_file)
        if not profile:
            continue
        profile["_file"] = model_file
        profiles.append(profile)
        if is_local_model_config(profile):
            static_model_ids.add(profile.get("model_id", ""))

    if include_dynamic_ollama:
        for installed in get_ollama_models():
            model_id = installed["name"]
            if model_id in static_model_ids:
                continue
            profile = _ollama_profile_from_model(installed)
            profile["_file"] = f"{OLLAMA_DYNAMIC_PREFIX}{model_id}"
            profiles.append(profile)

    return profiles


def display_model_selection(models: List[Dict[str, Any]]) -> None:
    """Display available models in a nice table format."""

    print("\n" + "=" * 80)
    print("🤖 AVAILABLE AI MODELS FOR LOCALITY PROCESSING")
    print("=" * 80)

    if not models:
        print("❌ No model profiles found in models/ directory")
        print("Please add model profile files to get started.")
        return

    for i, model in enumerate(models, 1):
        print(f"\n[{i}] {model['name']} ({model['provider']})")
        print(f"    💰 Cost per record: ${model['estimated_cost_per_record']:.4f}")
        print(
            f"    ⚡ Speed: {model['speed']} | 🎯 Accuracy: {model['accuracy']} | 💡 Cost Efficiency: {model['cost_efficiency']}"
        )
        print(
            f"    📊 Rate limit: {model['requests_per_minute']} req/min | 🔤 Max tokens: {model['max_output_tokens']:,}"
        )
        print(f"    🎯 Best for: {model['best_for']}")

        # Check if API key is configured
        if model["api_key"] and len(model["api_key"]) > 10:
            print(f"    🔑 API Key: Configured ({model['api_key'][:15]}...)")
        else:
            print(f"    ⚠️  API Key: Not configured")

    print("\n" + "=" * 80)


def select_model_interactive() -> Optional[Dict[str, Any]]:
    """Interactive model selection with user input."""

    # Discover available models
    model_files = discover_models()

    if not model_files:
        print("❌ No model profiles found!")
        print("Create model profile files in the models/ directory first.")
        return None

    # Load model profiles
    models = []
    for model_file in model_files:
        profile = load_model_profile(model_file)
        if profile:
            models.append(profile)

    if not models:
        print("❌ No valid model profiles could be loaded!")
        return None

    # Display models
    display_model_selection(models)

    # Get user selection
    while True:
        try:
            print(f"\nSelect a model (1-{len(models)}) or 'q' to quit: ", end="")
            choice = input().strip().lower()

            if choice == "q":
                print("Model selection cancelled.")
                return None

            model_index = int(choice) - 1

            if 0 <= model_index < len(models):
                selected_model = models[model_index]

                # Validate API key
                if not selected_model["api_key"] or len(selected_model["api_key"]) < 10:
                    print(
                        f"\n⚠️  Warning: {selected_model['name']} has no API key configured!"
                    )
                    print(
                        f"Edit models/{model_files[model_index]}.py to add your API key."
                    )
                    continue_anyway = input("Continue anyway? (y/n): ").strip().lower()
                    if continue_anyway != "y":
                        continue

                print(f"\n✅ Selected: {selected_model['name']}")
                print(
                    f"💰 Estimated cost per record: ${selected_model['estimated_cost_per_record']:.4f}"
                )
                return selected_model
            else:
                print(f"Please enter a number between 1 and {len(models)}")

        except ValueError:
            print("Please enter a valid number or 'q' to quit")
        except KeyboardInterrupt:
            print("\nModel selection cancelled.")
            return None


def calculate_batch_cost(
    model: Dict[str, Any], num_records: int, batch_size: int
) -> Dict[str, float]:
    """Calculate estimated costs for batch processing."""

    num_batches = (num_records + batch_size - 1) // batch_size  # Round up

    # Rough estimates based on typical prompt sizes
    avg_input_tokens_per_batch = 1600 + (batch_size * 100)  # Base prompt + record data
    avg_output_tokens_per_batch = batch_size * 130  # Estimated output per record

    total_input_tokens = num_batches * avg_input_tokens_per_batch
    total_output_tokens = num_batches * avg_output_tokens_per_batch

    input_cost = (total_input_tokens / 1000) * model["cost_per_1k_input"]
    output_cost = (total_output_tokens / 1000) * model["cost_per_1k_output"]
    total_cost = input_cost + output_cost

    estimated_time_minutes = num_batches * (60 / model["requests_per_minute"])

    return {
        "total_cost": total_cost,
        "input_cost": input_cost,
        "output_cost": output_cost,
        "num_batches": num_batches,
        "estimated_time_minutes": estimated_time_minutes,
        "cost_per_record": total_cost / num_records if num_records > 0 else 0,
    }


def get_model_by_name(model_name: str) -> Optional[Dict[str, Any]]:
    """Get a specific model by its file name."""
    return load_model_profile(model_name)


if __name__ == "__main__":
    # Test the model selection system
    print("🧪 Testing Model Selection System")
    selected = select_model_interactive()

    if selected:
        print(f"\nTest successful! Selected model: {selected['name']}")

        # Test cost calculation
        costs = calculate_batch_cost(selected, 100, 8)
        print(f"Cost for 100 records: ${costs['total_cost']:.4f}")
        print(f"Estimated time: {costs['estimated_time_minutes']:.1f} minutes")
    else:
        print("No model selected.")
