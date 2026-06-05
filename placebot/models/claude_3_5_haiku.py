# Claude 3.5 Haiku Model Profile with Prompt Caching Support
# Anthropic Claude API Configuration with Enhanced Cost Efficiency

MODEL_NAME = "Claude 3.5 Haiku (Cached)"
MODEL_PROVIDER = "Anthropic"
MODEL_ID = "claude-3-5-haiku-20241022"
API_ENDPOINT = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"

# API Key Configuration
# IMPORTANT: Add your API key here or set ANTHROPIC_API_KEY environment variable
# Get your key at: https://console.anthropic.com/
API_KEY = ""  # Leave blank: set ANTHROPIC_API_KEY in your environment or via the GUI

# Pricing Information (USD) with Caching - July 2025
# Note: Verify current pricing at https://console.anthropic.com/
COST_PER_1K_INPUT_TOKENS = 0.00025     # $0.25 per 1M input tokens (estimated)
COST_PER_1K_OUTPUT_TOKENS = 0.00125    # $1.25 per 1M output tokens (estimated)
COST_PER_1K_CACHED_TOKENS = 0.000025   # $0.025 per 1M cached tokens (90% savings!)

# Updated cost per record with caching (shows savings on large datasets)
ESTIMATED_COST_PER_RECORD = 0.0001     # 83% savings on 1000+ records

# Model Capabilities and Limits
MAX_TOKENS = 200000          # Context window
MAX_OUTPUT_TOKENS = 4096     # Max output tokens per request
CONTEXT_WINDOW = 200000      # 200k token context window
REQUESTS_PER_MINUTE = 50     # Conservative rate limit

# Model Characteristics
SPEED = "Fast"
ACCURACY = "High"
COST_EFFICIENCY = "Excellent (with caching)"
BEST_FOR = "High-volume processing, cost-sensitive applications with repeated instructions, fastest response times"

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
    except (KeyError, IndexError) as e:
        raise ValueError(f"Unexpected response format: {e}")
