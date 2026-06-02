import os
from openai import OpenAI
from groq import Groq


def get_llm_client() -> tuple:
    """Return (client, model_name) based on LLM_PROVIDER env var."""
    provider = os.getenv("LLM_PROVIDER", "groq").lower()

    if provider == "openai":
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        model = os.getenv("OPENAI_MODEL", "gpt-4o")
    elif provider == "groq":
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    else:
        raise ValueError(f"Unsupported LLM_PROVIDER: '{provider}'. Choose 'openai' or 'groq'.")

    return client, model


def chat(messages: list[dict], temperature: float = 0.0) -> str:
    """Send messages to the active LLM and return the response text."""
    client, model = get_llm_client()
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
    )
    return response.choices[0].message.content
