#!/usr/bin/env python3
"""
Model Comparison Tool for Locality Processor
============================================

Compares available models by speed, cost, and capabilities.
"""

from typing import List, Dict, Any
from .cost_estimator import CostEstimator


class ModelComparison:
    """Compares and ranks models for selection."""

    @staticmethod
    def compare_models(
        model_configs: List[Dict[str, Any]],
        num_records: int = 100,
        processing_mode: str = "realtime",
    ) -> List[Dict[str, Any]]:
        """
        Compare multiple models.

        Args:
            model_configs: List of model configurations
            num_records: Number of records for cost estimation
            processing_mode: 'realtime' or 'batch'

        Returns:
            List of model comparisons with rankings
        """
        comparisons = []

        for config in model_configs:
            model_name = config.get("name", "Unknown")
            has_caching = "cached" in model_name.lower()

            # Get cost estimate
            cost_est = CostEstimator.estimate_cost(
                num_records, config, processing_mode, with_caching=has_caching
            )

            # Build comparison entry
            comparison = {
                "model_name": model_name,
                "model_type": config.get("type", "cloud"),
                "vendor": ModelComparison._get_vendor(model_name),
                "estimated_cost": cost_est["estimated_cost"],
                "cost_per_record": cost_est["cost_per_record"],
                "has_caching": has_caching,
                "cache_savings": cost_est["cache_savings"],
                "input_cost_per_million": config.get("input_cost_per_million", 0),
                "output_cost_per_million": config.get("output_cost_per_million", 0),
                "requests_per_minute": config.get("requests_per_minute", 50),
                "estimated_time_minutes": ModelComparison._estimate_time(
                    num_records, config
                ),
                "is_local": config.get("type", "cloud") == "local",
            }

            comparisons.append(comparison)

        return comparisons

    @staticmethod
    def _get_vendor(model_name: str) -> str:
        """Determine vendor from model name."""
        name_lower = model_name.lower()
        if "openrouter" in name_lower:
            return "OpenRouter"
        elif "claude" in name_lower:
            return "Anthropic"
        elif "gpt" in name_lower or "o1" in name_lower or "o4" in name_lower:
            return "OpenAI"
        elif "gemini" in name_lower:
            return "Google"
        elif "qwen" in name_lower:
            return "Local (Ollama)"
        else:
            return "Unknown"

    @staticmethod
    def _estimate_time(num_records: int, config: Dict[str, Any]) -> float:
        """Estimate processing time in minutes."""
        rpm = config.get("requests_per_minute", 50)
        if rpm == 0:
            rpm = 50  # Default

        total_minutes = num_records / rpm
        return round(total_minutes, 1)

    @staticmethod
    def display_comparison(comparisons: List[Dict[str, Any]], sort_by: str = "cost"):
        """
        Display formatted model comparison table.

        Args:
            comparisons: List of model comparison dicts
            sort_by: Sort key ('cost', 'speed', 'name')
        """
        if not comparisons:
            print("❌ No models to compare")
            return

        # Sort comparisons
        if sort_by == "cost":
            comparisons = sorted(comparisons, key=lambda x: x["estimated_cost"])
        elif sort_by == "speed":
            comparisons = sorted(comparisons, key=lambda x: x["estimated_time_minutes"])
        elif sort_by == "name":
            comparisons = sorted(comparisons, key=lambda x: x["model_name"])

        print("\n🔍 MODEL COMPARISON")
        print("=" * 100)
        print(
            f"{'Rank':<6} {'Model Name':<30} {'Vendor':<15} {'Cost':<12} {'Time':<10} {'Caching':<10}"
        )
        print("-" * 100)

        for i, comp in enumerate(comparisons, 1):
            cost_str = (
                f"${comp['estimated_cost']:.4f}" if not comp["is_local"] else "FREE"
            )
            time_str = f"{comp['estimated_time_minutes']:.1f} min"
            cache_str = "✅ Yes" if comp["has_caching"] else "❌ No"

            print(
                f"{i:<6} {comp['model_name']:<30} {comp['vendor']:<15} "
                f"{cost_str:<12} {time_str:<10} {cache_str:<10}"
            )

        print("=" * 100)

        # Show best options
        if not any(c["is_local"] for c in comparisons):
            cheapest = min(comparisons, key=lambda x: x["estimated_cost"])
            print(
                f"\n💰 Most Cost-Effective: {cheapest['model_name']} "
                f"(${cheapest['estimated_cost']:.4f})"
            )

        fastest = min(comparisons, key=lambda x: x["estimated_time_minutes"])
        print(
            f"⚡ Fastest: {fastest['model_name']} "
            f"({fastest['estimated_time_minutes']:.1f} minutes)"
        )

        local_models = [c for c in comparisons if c["is_local"]]
        if local_models:
            print(f"🔒 Local/Free Options: {len(local_models)} models (no API costs)")

        print()
