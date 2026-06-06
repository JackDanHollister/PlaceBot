# OpenAI GPT-5 Model Profile
# OpenAI's current-generation flagship model with automatic prompt caching

MODEL_NAME = "GPT-5"
MODEL_PROVIDER = "OpenAI"
MODEL_ID = "gpt-5"
API_ENDPOINT = "https://api.openai.com/v1/chat/completions"
API_VERSION = "v1"

# API Key Configuration
# IMPORTANT: Add your API key here or set OPENAI_API_KEY environment variable
# Get your key at: https://platform.openai.com/api-keys
API_KEY = ""  # Leave blank: set OPENAI_API_KEY in your environment or via the GUI

# Pricing Information (USD) with Automatic Caching
# Note: Verify current pricing at https://platform.openai.com/docs/pricing
COST_PER_1K_INPUT_TOKENS = 0.00125     # $1.25 per 1M input tokens
COST_PER_1K_OUTPUT_TOKENS = 0.01       # $10.00 per 1M output tokens
COST_PER_1K_CACHED_TOKENS = 0.000125   # ~$0.125 per 1M cached input tokens
ESTIMATED_COST_PER_RECORD = 0.0006     # premium quality, cost-efficient with caching

# Model Capabilities and Limits
MAX_TOKENS = 400000          # Context window
MAX_OUTPUT_TOKENS = 16384    # Max output tokens per request
CONTEXT_WINDOW = 400000      # Large context window
REQUESTS_PER_MINUTE = 10000  # Rate limit (paid tier)

# Model Characteristics
SPEED = "Moderate"
ACCURACY = "Highest"
COST_EFFICIENCY = "Good"
CACHING = "Automatic"
BEST_FOR = "Complex reasoning, highest-quality extraction, instruction following"

# Special Headers for API
def get_headers(api_key: str) -> dict:
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

# Request format for OpenAI API.
# Note: GPT-5 uses `max_completion_tokens` (not `max_tokens`) and does not accept
# sampling parameters (temperature/top_p) on chat completions, so they are omitted.
def format_request(prompt: str, max_tokens: int = MAX_OUTPUT_TOKENS, cached_content_name: str = None) -> dict:
    return {
        "model": MODEL_ID,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "max_completion_tokens": min(max_tokens, MAX_OUTPUT_TOKENS)
    }

# Response parser for OpenAI API
def parse_response(response_json: dict) -> str:
    try:
        content = response_json['choices'][0]['message']['content']

        # Clean up any markdown formatting that OpenAI might add
        if content.startswith('```json'):
            content = content.replace('```json', '').replace('```', '').strip()
        elif content.startswith('```'):
            content = content.replace('```', '').strip()
        # Remove any leading text before JSON
        if '{' in content:
            content = content[content.find('{'):]
        if '}' in content:
            content = content[:content.rfind('}') + 1]

        return content
    except (KeyError, IndexError) as e:
        raise ValueError(f"Unexpected OpenAI response format: {e}")
