# OpenAI GPT-4.1-mini Model Profile
# OpenAI's Latest Cost-Optimized Model with 83% Cost Reduction and Automatic Caching

MODEL_NAME = "GPT-4.1-mini"
MODEL_PROVIDER = "OpenAI"
MODEL_ID = "gpt-4.1-mini-2025-04-14"
API_ENDPOINT = "https://api.openai.com/v1/chat/completions"
API_VERSION = "v1"

# API Key Configuration
# IMPORTANT: Add your API key here or set OPENAI_API_KEY environment variable
# Get your key at: https://platform.openai.com/api-keys
API_KEY = "your_openai_api_key_here"  # Replace with your actual API key

# Pricing Information (USD) with Automatic Caching - July 2025
# Prompt Caching: Automatic 50% discount on cached input tokens (>1,024 tokens)
COST_PER_1K_INPUT_TOKENS = 0.000255    # $0.255 per 1M input tokens (83% cheaper than GPT-4o-mini)
COST_PER_1K_OUTPUT_TOKENS = 0.001      # $1.00 per 1M output tokens
COST_PER_1K_CACHED_TOKENS = 0.0001275  # $0.1275 per 1M cached tokens (50% discount)
ESTIMATED_COST_PER_RECORD = 0.00008    # 83% cost reduction vs GPT-4o-mini

# Model Capabilities and Limits
MAX_TOKENS = 1000000         # 1M token context window!
MAX_OUTPUT_TOKENS = 16384    # Max output tokens per request
CONTEXT_WINDOW = 1000000     # 1M token context window
REQUESTS_PER_MINUTE = 10000  # Rate limit (paid tier)

# Model Characteristics
SPEED = "Very Fast"          # Nearly 50% faster than GPT-4o-mini
ACCURACY = "High"            # Matches or exceeds GPT-4o
COST_EFFICIENCY = "Excellent" # 83% cost reduction
CACHING = "Automatic"        # Automatic prompt caching (50% savings)
BEST_FOR = "High-volume processing, cost-sensitive applications, fastest responses"

# Special Headers for API with Caching Detection
def get_headers(api_key: str) -> dict:
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

# Request format for OpenAI API (Caching is automatic for prompts >1,024 tokens)
def format_request(prompt: str, max_tokens: int = MAX_OUTPUT_TOKENS, cached_content_name: str = None) -> dict:
    return {
        "model": MODEL_ID,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "max_tokens": min(max_tokens, MAX_OUTPUT_TOKENS),
        "temperature": 0.1,  # Low temperature for consistent locality processing
        "top_p": 0.8,
        "frequency_penalty": 0,
        "presence_penalty": 0
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
