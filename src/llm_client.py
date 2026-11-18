"""
Thin wrapper around the Gemini API.

The rest of the app only depends on one method, `generate_json(prompt)`, so a
fake client can stand in for Gemini in tests and in offline mode.
"""

import json
import logging
import os
import time
from typing import Any, Dict, Optional

logger = logging.getLogger("music_assistant.llm")

# Override with GEMINI_MODEL in .env if this model name changes.
DEFAULT_MODEL = "gemini-flash-lite-latest"
MAX_ATTEMPTS = 3


class LLMError(RuntimeError):
    """Raised when the LLM is unavailable or returns something unusable."""


def parse_json_text(text: str) -> Dict[str, Any]:
    """Parses a JSON object from model output, tolerating ```json fences."""
    cleaned = (text or "").strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise LLMError(f"Model did not return valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise LLMError("Model returned JSON that is not an object.")
    return data


class GeminiClient:
    """Calls Gemini and returns parsed JSON objects."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        key = api_key or os.getenv("GEMINI_API_KEY")
        if not key:
            raise LLMError(
                "Missing GEMINI_API_KEY. Copy .env.example to .env and add your key, "
                "or run with --offline."
            )
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:
            raise LLMError("google-genai is not installed. Run: pip install -r requirements.txt") from exc

        self._types = types
        self.client = genai.Client(api_key=key)
        self.model = model or os.getenv("GEMINI_MODEL") or DEFAULT_MODEL

    def generate_json(self, prompt: str, temperature: float = 0.0) -> Dict[str, Any]:
        """Sends a prompt and returns the JSON object the model replies with."""
        config = self._types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=temperature,
        )
        last_error: Optional[Exception] = None
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                response = self.client.models.generate_content(
                    model=self.model, contents=prompt, config=config
                )
                return parse_json_text(response.text or "")
            except LLMError:
                raise
            except Exception as exc:  # network errors, rate limits, server errors
                last_error = exc
                rate_limited = "429" in str(exc) or "RESOURCE_EXHAUSTED" in str(exc)
                logger.warning("Gemini call failed (attempt %d/%d): %s", attempt, MAX_ATTEMPTS, exc)
                if attempt < MAX_ATTEMPTS:
                    time.sleep(10 * attempt if rate_limited else 2 * attempt)
        raise LLMError(f"Gemini call failed after {MAX_ATTEMPTS} attempts: {last_error}")
