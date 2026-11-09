import os
from pathlib import Path

import requests
from dotenv import load_dotenv
from openai import NotFoundError, OpenAI, RateLimitError

load_dotenv(Path(__file__).resolve().parent.parent / "backend" / ".env")

CF_BASE = (
    "https://api.cloudflare.com/client/v4/accounts/"
    f"{os.environ["CLOUDFLARE_ACCOUNT_ID"]}/ai/run"
)
CF_HEADERS = {
    "Authorization": f"Bearer {os.environ["CLOUDFLARE_API_TOKEN"]}",
}
EMBED_MODEL = "@cf/baai/bge-m3"
LLM_MODEL = "qwen/qwen3.8-27b"
FALLBACK_LLM_MODEL = "openai/gpt-oss-120b"

_groq = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=os.environ["GROQ_API_KEY"],
)


def _cloudflare(model, payload):
    response = requests.post(f"{CF_BASE}/{model}", headers=CF_HEADERS, json=payload, timeout=60)
    response.raise_for_status()
    body = response.json()
    if not body.get("success", True):
        raise RuntimeError(f"Cloudflare error: {body.get('errors')}")
    return body["result"]


def embed(texts, batch_size=50):
    vectors = []
    for start in range(0, len(texts), batch_size):
        batch = texts[start: start + batch_size]
        vectors.extend(_cloudflare(EMBED_MODEL, {"text": batch})["data"])
    return vectors


def chat(messages, temperature=0):
    for model in (LLM_MODEL, FALLBACK_LLM_MODEL):
        try:
            reply = _groq.chat.completions.create(
                model=model, messages=messages, temperature=temperature
            )
            return reply.choices[0].message.content
        except (RateLimitError, NotFoundError):
            continue
    raise RuntimeError("All groq models are unavailable at this moment.")