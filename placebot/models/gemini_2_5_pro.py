# Gemini 2.5 Pro Model Profile with Advanced Thinking
# Google's most advanced model with state-of-the-art reasoning and implicit caching

MODEL_NAME = "Gemini 2.5 Pro"
MODEL_PROVIDER = "Google"
MODEL_ID = "gemini-2.5-pro"
API_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent"

# API Key Configuration
# IMPORTANT: Add your API key here or set GOOGLE_API_KEY environment variable
# Get your key at: https://aistudio.google.com/app/apikey
API_KEY = "your_google_api_key_here"  # Replace with your actual API key

# Pricing Information (USD) with Implicit Caching - July 2025
# Implicit Caching: Automatic 75% discount on cached input tokens (>2,048 tokens)
COST_PER_1K_INPUT_TOKENS = 0.00125    # $1.25 per 1M input tokens
COST_PER_1K_OUTPUT_TOKENS = 0.005     # $5.00 per 1M output tokens
COST_PER_1K_CACHED_TOKENS = 0.0003125 # $0.3125 per 1M cached tokens (75% discount)
ESTIMATED_COST_PER_RECORD = 0.0008    # Premium model with caching savings

# Model Capabilities and Limits  
MAX_TOKENS = 1000000         # 1M token context window
MAX_OUTPUT_TOKENS = 8192     # Max output tokens per request
CONTEXT_WINDOW = 1000000     # 1M token context window
REQUESTS_PER_MINUTE = 360    # Rate limit (more restricted)

# Model Characteristics
SPEED = "Moderate"           # Thinking models take more time
ACCURACY = "Highest"         # State-of-the-art performance
COST_EFFICIENCY = "Good"     # Premium pricing but powerful
CACHING = "Implicit"         # Automatic caching (75% savings) 
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
