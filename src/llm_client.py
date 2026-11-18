"""
Thin wrapper around the Gemini API.

The rest of the app only depends on one method, `generate_json(prompt)`, so a
fake client can stand in for Gemini in tests and in offline mode.
"""

import json
import logging
import os
import re
import time
from typing import Any, Dict, Optional

logger = logging.getLogger("music_assistant.llm")

# Override with GEMINI_MODEL in .env if this model name changes.
DEFAULT_MODEL = "gemini-3.5-flash-lite"
MAX_ATTEMPTS = 3
# Free tier allows ~15 requests/minute; space calls out to stay under it.
MIN_SECONDS_BETWEEN_CALLS = float(os.getenv("GEMINI_MIN_INTERVAL", "4.2"))


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
        self._last_call = 0.0

    def _throttle(self) -> None:
        wait = MIN_SECONDS_BETWEEN_CALLS - (time.monotonic() - self._last_call)
        if wait > 0:
            time.sleep(wait)
        self._last_call = time.monotonic()

    def generate_json(self, prompt: str, temperature: float = 0.0) -> Dict[str, Any]:
        """Sends a prompt and returns the JSON object the model replies with."""
        config = self._types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=temperature,
        )
        last_error: Optional[Exception] = None
        for attempt in range(1, MAX_ATTEMPTS + 1):
            self._throttle()
            try:
                response = self.client.models.generate_content(
                    model=self.model, contents=prompt, config=config
                )
                return parse_json_text(response.text or "")
            except LLMError:
                raise
            except Exception as exc:  # network errors, rate limits, server errors
                last_error = exc
                message = str(exc)
                rate_limited = "429" in message or "RESOURCE_EXHAUSTED" in message
                # Bad key, bad model name, bad request: retrying will not help.
                permanent = any(code in message for code in ("400", "401", "403", "404"))
                logger.warning("Gemini call failed (attempt %d/%d): %s", attempt, MAX_ATTEMPTS, exc)
                if permanent:
                    break
                if attempt < MAX_ATTEMPTS:
                    # Honour the server's "retry in Ns" hint when it gives one.
                    hint = re.search(r"retry in ([\d.]+)s", message)
                    delay = float(hint.group(1)) + 1 if hint else (15 * attempt if rate_limited else 2 * attempt)
                    logger.info("Retrying in %.0fs", delay)
                    time.sleep(min(delay, 70))
        raise LLMError(f"Gemini call failed: {last_error}")
