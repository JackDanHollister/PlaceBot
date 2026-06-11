"""OpenRouter GPT-4.1 profile."""

from placebot.models.__openrouter_common import (
    API_ENDPOINT,
    format_chat_request,
    get_headers,
    parse_response,
)

MODEL_NAME = "OpenRouter: GPT-4.1"
MODEL_PROVIDER = "OpenRouter"
MODEL_ID = "openai/gpt-4.1"
API_KEY = ""
MAX_OUTPUT_TOKENS = 8192
REQUESTS_PER_MINUTE = 200
REQUEST_TIMEOUT = 120

COST_PER_1K_INPUT_TOKENS = 0.002
COST_PER_1K_OUTPUT_TOKENS = 0.008
ESTIMATED_COST_PER_RECORD = 0.0008

SPEED = "Fast"
ACCURACY = "Very High"
COST_EFFICIENCY = "Good"
BEST_FOR = "One-key OpenRouter workflows, strong OpenAI baseline"


def format_request(
    prompt: str, max_tokens: int = MAX_OUTPUT_TOKENS, cached_content_name: str = None
) -> dict:
    return format_chat_request(MODEL_ID, prompt, max_tokens, MAX_OUTPUT_TOKENS)
