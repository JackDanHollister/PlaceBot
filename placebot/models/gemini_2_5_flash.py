# Gemini 2.5 Flash Model Profile with Implicit Caching
# Google's latest stable model with best price-performance and automatic caching

MODEL_NAME = "Gemini 2.5 Flash"
MODEL_PROVIDER = "Google"
MODEL_ID = "gemini-2.5-flash"
API_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

# API Key Configuration
# IMPORTANT: Add your API key here or set GOOGLE_API_KEY environment variable
# Get your key at: https://aistudio.google.com/app/apikey
API_KEY = ""  # Leave blank: set GOOGLE_API_KEY in your environment or via the GUI

# Pricing Information (USD) with Implicit Caching - July 2025
# Implicit Caching: Automatic 75% discount on cached input tokens (>1,024 tokens)
COST_PER_1K_INPUT_TOKENS = 0.000125   # $0.125 per 1M input tokens
COST_PER_1K_OUTPUT_TOKENS = 0.000375  # $0.375 per 1M output tokens
COST_PER_1K_CACHED_TOKENS = 0.00003125 # $0.03125 per 1M cached tokens (75% discount)
ESTIMATED_COST_PER_RECORD = 0.0001    # Extremely cost-effective with caching

# Model Capabilities and Limits
MAX_TOKENS = 1000000         # 1M token context window
MAX_OUTPUT_TOKENS = 8192     # Max output tokens per request
CONTEXT_WINDOW = 1000000     # 1M token context window
REQUESTS_PER_MINUTE = 1000   # Rate limit

# Model Characteristics
SPEED = "Very Fast"           # Optimized for speed
ACCURACY = "High"             # Well-rounded capabilities
COST_EFFICIENCY = "Excellent" # Best price-performance
CACHING = "Implicit"          # Automatic caching (75% savings)
REASONING = "Adaptive"        # Thinking capabilities built-in
BEST_FOR = "High-volume processing, cost-sensitive applications, balanced performance"

# Special Headers for API
def get_headers(api_key: str) -> dict:
    return {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key
    }

# Request format for Gemini API (Implicit caching automatic for prompts >1,024 tokens)
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
