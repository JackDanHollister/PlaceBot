"""Shared OpenRouter profile helpers."""

API_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"


def get_headers(api_key: str) -> dict:
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "https://github.com/JackDanHollister/PlaceBot",
        "X-OpenRouter-Title": "PlaceBot",
    }


def format_chat_request(
    model_id: str,
    prompt: str,
    max_tokens: int,
    max_output_tokens: int,
) -> dict:
    return {
        "model": model_id,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": min(max_tokens, max_output_tokens),
        "temperature": 0.1,
        "top_p": 0.8,
        "response_format": {"type": "json_object"},
    }


def parse_response(response_json: dict) -> str:
    try:
        content = response_json["choices"][0]["message"]["content"]
        if content.startswith("```json"):
            content = content.replace("```json", "").replace("```", "").strip()
        elif content.startswith("```"):
            content = content.replace("```", "").strip()
        if "{" in content:
            content = content[content.find("{") :]
        if "}" in content:
            content = content[: content.rfind("}") + 1]
        return content
    except (KeyError, IndexError, TypeError) as e:
        raise ValueError(f"Unexpected OpenRouter response format: {e}")
