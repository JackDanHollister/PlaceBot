# OpenAI o4-mini Model Profile  
# OpenAI's Latest Compact Reasoning Model with Automatic Caching

MODEL_NAME = "o4-mini"
MODEL_PROVIDER = "OpenAI"
MODEL_ID = "o4-mini-2025-04-16"
API_ENDPOINT = "https://api.openai.com/v1/chat/completions"
API_VERSION = "v1"

# API Key Configuration
# IMPORTANT: Add your API key here or set OPENAI_API_KEY environment variable
# Get your key at: https://platform.openai.com/api-keys
API_KEY = "your_openai_api_key_here"  # Replace with your actual API key

# Pricing Information (USD) with Automatic Caching - July 2025
# Prompt Caching: Automatic 50% discount on cached input tokens (>1,024 tokens)
COST_PER_1K_INPUT_TOKENS = 0.0003      # $0.30 per 1M input tokens (cost-efficient reasoning)
COST_PER_1K_OUTPUT_TOKENS = 0.0012     # $1.20 per 1M output tokens
COST_PER_1K_CACHED_TOKENS = 0.00015    # $0.15 per 1M cached tokens (50% discount)
ESTIMATED_COST_PER_RECORD = 0.0004     # Excellent cost/performance for reasoning

# Model Capabilities and Limits
MAX_TOKENS = 128000          # Context window
MAX_OUTPUT_TOKENS = 65536    # Max output tokens per request
CONTEXT_WINDOW = 128000      # 128k token context window
REQUESTS_PER_MINUTE = 10000  # Rate limit (paid tier)

# Model Characteristics
SPEED = "Fast"               # Optimized for fast reasoning
ACCURACY = "High"            # Best-performing on AIME 2024 and 2025
COST_EFFICIENCY = "Excellent" # Cost-efficient reasoning model
CACHING = "Automatic"        # Automatic prompt caching (50% savings)
REASONING = "Advanced"       # Designed for math, coding, visual tasks
BEST_FOR = "Fast reasoning tasks, math problems, coding challenges, cost-efficient thinking"

# Special Headers for API with Caching Detection
def get_headers(api_key: str) -> dict:
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

# Request format for OpenAI API (Caching is automatic for prompts >1,024 tokens)
def format_request(prompt: str, max_tokens: int = MAX_OUTPUT_TOKENS, cached_content_name: str = None) -> dict:
    # o4-mini is very restrictive - only supports basic parameters
    return {
        "model": MODEL_ID,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ]
        # Note: o4-mini only supports default parameters - no temperature, top_p, max_tokens, etc.
        # All other parameters cause API errors
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
