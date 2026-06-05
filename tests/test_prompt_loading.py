"""Verify the instruction prompt loads from placebot/data/prompt.md."""

from placebot.core.ai_processor import AIProcessor


def _processor():
    return AIProcessor(
        {
            "name": "Test Model",
            "api_key": "test-key",
            "requests_per_minute": 50,
        }
    )


def test_prompt_loads_and_is_non_trivial():
    prompt = _processor()._get_full_instructions()
    assert isinstance(prompt, str)
    assert len(prompt) > 100


def test_prompt_is_cached_between_calls():
    proc = _processor()
    assert proc._get_full_instructions() is proc._get_full_instructions()
