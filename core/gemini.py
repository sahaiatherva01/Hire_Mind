import os
import json
from typing import Optional, Dict, Any, List
import numpy as np

from config import Config

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None

_GEMINI_CLIENT = None


def get_gemini_client():
    global _GEMINI_CLIENT
    if _GEMINI_CLIENT is not None:
        return _GEMINI_CLIENT

    key = Config.GEMINI_API_KEY
    if key and not key.startswith("your_") and genai:
        try:
            _GEMINI_CLIENT = genai.Client(api_key=key)
        except Exception:
            _GEMINI_CLIENT = None
    return _GEMINI_CLIENT


def embed_text(text: str) -> List[float]:
    """Generates a 768-dimensional embedding vector for text using Gemini or deterministic fallback."""
    text = (text or "").strip()
    dim = 768
    if not text:
        return [0.0] * dim

    client = get_gemini_client()
    if client:
        try:
            response = client.models.embed_content(
                model=Config.EMBEDDING_MODEL,
                contents=text,
            )
            if hasattr(response, "embedding") and response.embedding:
                return response.embedding.values
            if hasattr(response, "embeddings") and response.embeddings:
                return response.embeddings[0].values
        except Exception:
            pass

    # Deterministic vocabulary-aware fallback for offline / development runs
    vec = np.zeros(dim, dtype=np.float32)
    words = text.lower().split()
    for idx, word in enumerate(words):
        h = hash(word) % dim
        weight = 1.0 / (1.0 + (idx * 0.05))
        vec[h] += weight
        vec[(h * 31) % dim] += weight * 0.5

    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    return vec.tolist()


def generate_text(prompt: str, system_instruction: Optional[str] = None, temperature: float = 0.2) -> str:
    """Generates text from Gemini using the pinned model."""
    client = get_gemini_client()
    if not client:
        return ""

    try:
        config_kwargs = {"temperature": temperature}
        if system_instruction:
            config_kwargs["system_instruction"] = system_instruction

        response = client.models.generate_content(
            model=Config.DEFAULT_MODEL,
            contents=prompt,
            config=config_kwargs
        )
        return response.text.strip() if response and response.text else ""
    except Exception:
        return ""


def generate_json(prompt: str, system_instruction: Optional[str] = None, temperature: float = 0.1) -> Optional[Dict[str, Any]]:
    """Generates structured JSON output from Gemini."""
    raw = generate_text(prompt, system_instruction=system_instruction, temperature=temperature)
    if not raw:
        return None

    cleaned = raw.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    if cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    try:
        return json.loads(cleaned)
    except Exception:
        return None
