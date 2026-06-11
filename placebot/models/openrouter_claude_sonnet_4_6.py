"""OpenRouter Claude Sonnet 4.6 profile."""

from placebot.models.__openrouter_common import (
    API_ENDPOINT,
    format_chat_request,
    get_headers,
    parse_response,
)

MODEL_NAME = "OpenRouter: Claude Sonnet 4.6"
MODEL_PROVIDER = "OpenRouter"
MODEL_ID = "anthropic/claude-sonnet-4.6"
API_KEY = ""
MAX_OUTPUT_TOKENS = 8192
REQUESTS_PER_MINUTE = 200
REQUEST_TIMEOUT = 120

COST_PER_1K_INPUT_TOKENS = 0.003
COST_PER_1K_OUTPUT_TOKENS = 0.015
ESTIMATED_COST_PER_RECORD = 0.0004

SPEED = "Medium"
ACCURACY = "Very High"
COST_EFFICIENCY = "Good"
BEST_FOR = "One-key OpenRouter workflows, balanced Claude quality"


def format_request(
    prompt: str, max_tokens: int = MAX_OUTPUT_TOKENS, cached_content_name: str = None
) -> dict:
    return format_chat_request(MODEL_ID, prompt, max_tokens, MAX_OUTPUT_TOKENS)
