"""OpenAI-compatible client pointed at LM Studio local endpoint."""
import os
from openai import OpenAI

_client: OpenAI | None = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        base_url = os.getenv("LM_STUDIO_URL", "http://localhost:1234/v1")
        _client = OpenAI(base_url=base_url, api_key="lm-studio")
    return _client


def chat_completion(messages: list[dict], temperature: float = 0.2, **kwargs) -> str:
    """Send messages to LM Studio and return the assistant reply text."""
    client = get_client()
    model = os.getenv("LM_STUDIO_MODEL", "local-model")
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        **kwargs,
    )
    return response.choices[0].message.content or ""
