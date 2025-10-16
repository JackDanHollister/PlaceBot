# Gemini 2.5 Flash-Lite Model Profile with Native Thinking
# Google's fastest and most cost-efficient 2.5 model with adaptive thinking

MODEL_NAME = "Gemini 2.5 Flash-Lite"
MODEL_PROVIDER = "Google"
MODEL_ID = "gemini-2.5-flash-lite"
API_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent"

# API Key Configuration
# IMPORTANT: Add your API key here or set GOOGLE_API_KEY environment variable
# Get your key at: https://aistudio.google.com/app/apikey
API_KEY = "your_google_api_key_here"  # Replace with your actual API key

# Pricing Information (USD) with Native Thinking - August 2025
# Native Thinking: Adaptive thinking with optional toggle for demanding tasks
COST_PER_1K_INPUT_TOKENS = 0.0001      # $0.10 per 1M input tokens (lowest cost!)
COST_PER_1K_OUTPUT_TOKENS = 0.0004     # $0.40 per 1M output tokens
ESTIMATED_COST_PER_RECORD = 0.00005    # Most cost-effective model in 2.5 family

# Model Capabilities and Limits
MAX_TOKENS = 1000000         # 1M token context window
MAX_OUTPUT_TOKENS = 8192     # Max output tokens per request
CONTEXT_WINDOW = 1000000     # 1M token context window
REQUESTS_PER_MINUTE = 1500   # Higher rate limits for lite model

# Model Characteristics
SPEED = "Fastest"            # Best in-class speed in 2.5 family
ACCURACY = "High"            # High-quality performance for size
COST_EFFICIENCY = "Excellent" # Lowest cost 2.5 model
THINKING = "Adaptive"        # Optional thinking capabilities
REASONING = "Selective"      # Thinking can be toggled for complex tasks
BEST_FOR = "High-volume processing, latency-sensitive tasks, translation, classification, cost-efficient operations"

# Special Headers for API
def get_headers(api_key: str) -> dict:
    return {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key
    }

# Request format for Gemini API (Adaptive thinking - toggleable for complex tasks)
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
