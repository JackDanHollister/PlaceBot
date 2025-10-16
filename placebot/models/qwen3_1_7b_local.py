# Qwen 3 1.7B Local Model Profile
# Alibaba Qwen 3 via Ollama - Local LLM Configuration

MODEL_NAME = "Qwen 3 1.7B (Local)"
MODEL_PROVIDER = "Alibaba (via Ollama)"
MODEL_ID = "qwen3:1.7b"
API_ENDPOINT = "http://localhost:11434/api/generate"
API_VERSION = "local"

# No API Key needed for local models!
API_KEY = None

# Pricing Information (USD) - Local = FREE!
COST_PER_1K_INPUT_TOKENS = 0.0         # FREE!
COST_PER_1K_OUTPUT_TOKENS = 0.0        # FREE!
ESTIMATED_COST_PER_RECORD = 0.0        # FREE!

# Model Capabilities and Limits
MAX_TOKENS = 32768           # Context window (Qwen 3 capacity)
MAX_OUTPUT_TOKENS = 8192     # Max output tokens per request
CONTEXT_WINDOW = 32768       # 32k token context window
REQUESTS_PER_MINUTE = 999999 # No rate limits locally (hardware dependent)

# Model Characteristics
SPEED = "Very Fast (RTX 4090)"
ACCURACY = "Good (1.7B parameter model)"
COST_EFFICIENCY = "Perfect (Free)"
BEST_FOR = "Privacy-focused, cost-free processing, offline capability"

# Special Headers for Ollama API
def get_headers(api_key: str = None) -> dict:
    return {
        "Content-Type": "application/json"
    }

# Request format for Ollama API
def format_request(prompt: str, max_tokens: int = MAX_OUTPUT_TOKENS, cached_content_name: str = None) -> dict:
    return {
        "model": MODEL_ID,
        "prompt": prompt,
        "stream": False,  # Get complete response at once
        "options": {
            "temperature": 0.1,     # Low temperature for consistent locality processing
            "top_p": 0.8,
            "num_ctx": min(CONTEXT_WINDOW, 8192),  # Context window size
            "num_predict": min(max_tokens, MAX_OUTPUT_TOKENS)
        }
    }

# Response parser for Ollama API
def parse_response(response_json: dict) -> str:
    try:
        return response_json['response']
    except KeyError as e:
        raise ValueError(f"Unexpected Ollama response format: {e}")

# Additional local model info
LOCAL_MODEL_INFO = {
    "hardware_requirements": "GPU recommended, 4GB+ VRAM ideal",
    "inference_speed": "~5-10 tokens/second on RTX 4090",
    "privacy": "Complete - data never leaves local machine",
    "offline_capable": True,
    "model_size": "~1GB"
}
