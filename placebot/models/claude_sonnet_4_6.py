# Claude Sonnet 4.6 Model Profile
# Anthropic's best balance of speed and intelligence, with prompt caching

MODEL_NAME = "Claude Sonnet 4.6 (Cached)"
MODEL_PROVIDER = "Anthropic"
MODEL_ID = "claude-sonnet-4-6"
API_ENDPOINT = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"

# API Key Configuration
# IMPORTANT: Add your API key here or set ANTHROPIC_API_KEY environment variable
# Get your key at: https://console.anthropic.com/
API_KEY = ""  # Leave blank: set ANTHROPIC_API_KEY in your environment or via the GUI

# Pricing Information (USD) with Caching
# Note: Verify current pricing at https://platform.claude.com/docs/en/about-claude/pricing
COST_PER_1K_INPUT_TOKENS = 0.003      # $3.00 per 1M input tokens
COST_PER_1K_OUTPUT_TOKENS = 0.015     # $15.00 per 1M output tokens
COST_PER_1K_CACHED_TOKENS = 0.0003    # ~$0.30 per 1M cached read tokens (90% savings!)

# Model configuration
MAX_OUTPUT_TOKENS = 8192               # Maximum output tokens per request
ESTIMATED_COST_PER_RECORD = 0.0004     # cost-efficient at scale with caching

# Rate limiting
REQUESTS_PER_MINUTE = 50

# Special Headers for API with Caching Support
def get_headers(api_key: str) -> dict:
    return {
        "Content-Type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01"
    }

# Request format for Claude API
def format_request(prompt: str, max_tokens: int = MAX_OUTPUT_TOKENS, cached_content_name: str = None) -> dict:
    request_body = {
        "model": MODEL_ID,
        "max_tokens": min(max_tokens, MAX_OUTPUT_TOKENS),
        "temperature": 0.1,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ]
    }

    # Add caching if cached_content_name is provided
    if cached_content_name:
        request_body["system"] = [
            {
                "type": "text",
                "text": "You are a geographic locality processing expert.",
                "cache_control": {"type": "ephemeral"}
            }
        ]

    return request_body

# Response parser for Claude API
def parse_response(response_json: dict) -> str:
    try:
        return response_json['content'][0]['text']
    except (KeyError, IndexError, TypeError) as e:
        raise ValueError(f"Failed to parse Claude response: {e}")
