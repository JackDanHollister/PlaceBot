"""Tests for model discovery and profile loading."""

from placebot.core.model_selector import discover_models, load_model_profile


def test_discover_models_finds_profiles():
    models = discover_models()
    assert "claude_haiku_4_5" in models
    assert all(not m.startswith("__") for m in models)


def test_load_profile_has_expected_keys():
    cfg = load_model_profile("claude_haiku_4_5")
    assert cfg is not None
    for key in (
        "name",
        "provider",
        "model_id",
        "input_cost_per_million",
        "output_cost_per_million",
        "type",
    ):
        assert key in cfg


def test_per_million_pricing_is_derived_from_per_1k():
    cfg = load_model_profile("claude_haiku_4_5")
    assert cfg["input_cost_per_million"] == cfg["cost_per_1k_input"] * 1000


def test_placeholder_api_keys_removed(isolated_home):
    # With no env key set, profiles should expose an empty key, not a placeholder
    cfg = load_model_profile("claude_haiku_4_5")
    assert "your_" not in (cfg["api_key"] or "")


def test_local_model_typed_as_local():
    models = discover_models()
    qwen = [m for m in models if "qwen" in m]
    if qwen:
        cfg = load_model_profile(qwen[0])
        assert cfg["type"] == "local"
