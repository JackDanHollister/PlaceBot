# Gemini 3.1 Pro Model Profile with Advanced Thinking
# Google's most advanced model with state-of-the-art reasoning.
# NOTE: this is a PREVIEW model. Google rotates Gemini Pro preview IDs every few
# months (e.g. gemini-3-pro-preview was shut down and replaced by this one).
# If you get a 404 "model no longer available", check the current Pro preview ID
# at https://ai.google.dev/gemini-api/docs/models and update MODEL_ID/endpoint.

MODEL_NAME = "Gemini 3.1 Pro"
MODEL_PROVIDER = "Google"
MODEL_ID = "gemini-3.1-pro-preview"
API_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-pro-preview:generateContent"

# API Key Configuration
# IMPORTANT: Add your API key here or set GOOGLE_API_KEY environment variable
# Get your key at: https://aistudio.google.com/app/apikey
API_KEY = ""  # Leave blank: set GOOGLE_API_KEY in your environment or via the GUI

# Pricing Information (USD) with Implicit Caching
# Note: Verify current pricing at https://ai.google.dev/gemini-api/docs/pricing
COST_PER_1K_INPUT_TOKENS = 0.002      # $2.00 per 1M input tokens
COST_PER_1K_OUTPUT_TOKENS = 0.012     # $12.00 per 1M output tokens
COST_PER_1K_CACHED_TOKENS = 0.0005    # ~$0.50 per 1M cached input tokens
ESTIMATED_COST_PER_RECORD = 0.0008    # premium model

# Model Capabilities and Limits
MAX_TOKENS = 1000000         # 1M token context window
MAX_OUTPUT_TOKENS = 8192     # Max output tokens per request
CONTEXT_WINDOW = 1000000     # 1M token context window
REQUESTS_PER_MINUTE = 360    # Rate limit (more restricted)

# Model Characteristics
SPEED = "Moderate"           # Thinking models take more time
ACCURACY = "Highest"         # State-of-the-art performance
COST_EFFICIENCY = "Good"     # Premium pricing but powerful
CACHING = "Implicit"         # Automatic caching
REASONING = "Advanced"       # Deep thinking capabilities
THINKING = "Adaptive"        # Built-in thinking mode
BEST_FOR = "Complex reasoning, coding, math, science, advanced analysis"

# Special Headers for API
def get_headers(api_key: str) -> dict:
    return {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key
    }

# Request format for Gemini API (Implicit caching automatic for prompts >2,048 tokens)
def format_request(prompt: str, max_tokens: int = MAX_OUTPUT_TOKENS, cached_content_name: str = None) -> dict:
    request_body = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": min(max_tokens, MAX_OUTPUT_TOKENS),
            "responseMimeType": "application/json"
        }
    }
    return request_body

# Response parser for Gemini API
def parse_response(response_json: dict) -> str:
    try:
        content = response_json['candidates'][0]['content']['parts'][0]['text']
        # Clean up any markdown formatting
        if content.startswith('```json'):
            content = content.replace('```json', '').replace('```', '').strip()
        return content
    except (KeyError, IndexError, TypeError) as e:
        raise ValueError(f"Failed to parse Gemini response: {e}")
