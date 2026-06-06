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


def test_current_model_lineup():
    models = discover_models()
    # Current OpenAI + Gemini lineup is present
    for expected in ("gpt_4_1", "gpt_4_1_mini", "gpt_5", "gpt_5_mini",
                     "gemini_3_5_flash", "gemini_3_pro"):
        assert expected in models, f"missing {expected}"
    # Retired / shut-down profiles are gone
    for removed in ("o4_mini", "gemini_2_5_flash", "gemini_2_5_flash_lite",
                    "gemini_2_5_pro"):
        assert removed not in models, f"{removed} should be removed"


def test_gpt5_request_shape():
    # GPT-5 must use max_completion_tokens and omit sampling params (else 400),
    # and use minimal reasoning effort so it returns quickly for extraction.
    import placebot.models.gpt_5 as gpt5
    body = gpt5.format_request("hello")
    assert "max_completion_tokens" in body
    assert "max_tokens" not in body
    assert "temperature" not in body and "top_p" not in body
    assert body.get("reasoning_effort") == "minimal"


def test_gpt5_has_longer_request_timeout():
    # Reasoning models need more than the 30s default HTTP timeout
    cfg = load_model_profile("gpt_5")
    assert cfg["request_timeout"] >= 120
    assert load_model_profile("gpt_4_1")["request_timeout"] == 30


def test_gpt41_keeps_classic_shape():
    import placebot.models.gpt_4_1 as gpt41
    body = gpt41.format_request("hello")
    assert "max_tokens" in body
    assert "temperature" in body
