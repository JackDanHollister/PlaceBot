"""Tests for model discovery and profile loading."""

from placebot.core.model_selector import (
    clear_model_caches,
    discover_models,
    get_ollama_models,
    get_ollama_models_cached,
    load_all_model_profiles,
    load_model_profile,
)


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
    for expected in (
        "gpt_4_1",
        "gpt_4_1_mini",
        "gpt_5",
        "gpt_5_mini",
        "gemini_3_5_flash",
        "gemini_3_1_pro",
    ):
        assert expected in models, f"missing {expected}"
    for expected in (
        "openrouter_gpt_5_mini",
        "openrouter_gpt_4_1",
        "openrouter_gemini_3_5_flash",
        "openrouter_claude_haiku_4_5",
        "openrouter_claude_sonnet_4_6",
        "openrouter_claude_opus_4_8",
    ):
        assert expected in models, f"missing {expected}"
    # Retired / shut-down profiles are gone
    for removed in (
        "o4_mini",
        "gemini_2_5_flash",
        "gemini_2_5_flash_lite",
        "gemini_2_5_pro",
        "gemini_3_pro",
    ):
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


def test_openrouter_profile_uses_openrouter_key(isolated_home):
    from placebot.core.config import Config

    Config().save_api_key("openrouter", "sk-or-v1-ABCDEFGHIJKLMNOP")
    cfg = load_model_profile("openrouter_gpt_5_mini")
    assert cfg["provider"] == "OpenRouter"
    assert cfg["api_key"] == "sk-or-v1-ABCDEFGHIJKLMNOP"
    assert cfg["api_endpoint"] == "https://openrouter.ai/api/v1/chat/completions"
    body = cfg["module"].format_request("hello", 123)
    assert body["model"] == "openai/gpt-5-mini"
    assert body["messages"][0]["content"] == "hello"
    assert body["response_format"] == {"type": "json_object"}


def test_get_ollama_models_handles_unavailable_server(monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError("no server")

    monkeypatch.setattr("placebot.core.model_selector.requests.get", fail)
    assert get_ollama_models() == []


def test_get_ollama_models_cached_avoids_repeat_probes(monkeypatch):
    calls = {"n": 0}

    def fake_probe(timeout=0.5):
        calls["n"] += 1
        return [{"name": "qwen3:8b", "size": 1, "details": {}}]

    monkeypatch.setattr("placebot.core.model_selector.get_ollama_models", fake_probe)

    first = get_ollama_models_cached()
    second = get_ollama_models_cached()
    assert first == second
    assert calls["n"] == 1  # second call served from cache

    assert get_ollama_models_cached(force_refresh=True) == first
    assert calls["n"] == 2

    clear_model_caches()
    get_ollama_models_cached()
    assert calls["n"] == 3


def test_get_ollama_models_cached_caches_failed_probe(monkeypatch):
    """An empty result (Ollama down) must be cached - that's the slow case."""
    calls = {"n": 0}

    def fake_probe(timeout=0.5):
        calls["n"] += 1
        return []

    monkeypatch.setattr("placebot.core.model_selector.get_ollama_models", fake_probe)

    assert get_ollama_models_cached() == []
    assert get_ollama_models_cached() == []
    assert calls["n"] == 1


def test_load_model_profile_reuses_module():
    first = load_model_profile("claude_haiku_4_5")
    second = load_model_profile("claude_haiku_4_5")
    assert first["module"] is second["module"]


def test_load_model_profile_reimports_on_mtime_change(tmp_path):
    import os
    import time as time_mod

    from placebot.core import model_selector

    models_dir = os.path.join(
        os.path.dirname(os.path.abspath(model_selector.__file__)), "..", "models"
    )
    file_path = os.path.abspath(os.path.join(models_dir, "claude_haiku_4_5.py"))

    first = load_model_profile("claude_haiku_4_5")
    # Bump the file's mtime without touching its contents
    new_time = time_mod.time() + 10
    os.utime(file_path, (new_time, new_time))
    try:
        second = load_model_profile("claude_haiku_4_5")
        assert first["module"] is not second["module"]
    finally:
        # Restore a sane mtime so subsequent runs aren't skewed
        now = time_mod.time()
        os.utime(file_path, (now, now))


def test_profile_api_key_fresh_after_env_change(isolated_home, monkeypatch):
    """Module caching must not freeze API-key availability (modules-only cache)."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    before = load_model_profile("claude_haiku_4_5")
    assert not before["api_key"]

    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-123")
    after = load_model_profile("claude_haiku_4_5")
    assert after["api_key"] == "sk-ant-test-123"


def test_dynamic_ollama_profiles_are_added(monkeypatch):
    monkeypatch.setattr(
        "placebot.core.model_selector.get_ollama_models",
        lambda timeout=0.5: [
            {
                "name": "qwen3.6:latest",
                "size": 123,
                "details": {
                    "family": "qwen35moe",
                    "parameter_size": "36B",
                    "quantization_level": "Q4_K_M",
                },
            }
        ],
    )

    profiles = load_all_model_profiles(include_dynamic_ollama=True)
    dynamic = [p for p in profiles if p.get("_file") == "ollama:qwen3.6:latest"]
    assert len(dynamic) == 1
    assert dynamic[0]["local_ready"] is True
    assert dynamic[0]["model_id"] == "qwen3.6:latest"
    assert dynamic[0]["module"].format_request("hello")["model"] == "qwen3.6:latest"
