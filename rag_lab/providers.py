import hashlib
import json
import os
from pathlib import Path

import requests
from dotenv import load_dotenv
from openai import NotFoundError, OpenAI, RateLimitError

load_dotenv(Path(__file__).resolve().parent.parent / "backend" / ".env")

_cache_path = None
_cache = {}

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


def enable_cache(path):
    global _cache_path
    _cache_path = Path(path)
    if _cache_path.exists():
        for line in _cache_path.read_text(encoding="utf-8").splitlines():
            entry = json.loads(line)
            _cache[entry["key"]] = (entry["text"], entry["model"])
            
            
def _cache_key(messages, models, temperature):
    raw = json.dumps(
        {"messages": messages, "models": list(models), "temperature": temperature},
        ensure_ascii=False,
        sort_keys=True
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _cache_store(key, text, model):
    _cache[key] = (text, model)
    with _cache_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"key": key, "text": text, "model": model}, ensure_ascii=False) + "\n")


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


def chat(messages, temperature=0, models=None):
    models = models or (LLM_MODEL, FALLBACK_LLM_MODEL)
    key = _cache_key(messages, models, temperature) if _cache_path else None
    if key in _cache:
        return _cache[key]
    
    for model in models or (LLM_MODEL, FALLBACK_LLM_MODEL):
        try:
            reply = _groq.chat.completions.create(
                model=model, messages=messages, temperature=temperature
            )
            text = reply.choices[0].message.content
            if key:
                _cache_store(key, text, model)
            return text, model
        except (RateLimitError, NotFoundError):
            continue
    raise RuntimeError("All groq models are unavailable at this moment.")