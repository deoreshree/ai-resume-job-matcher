"""Small OpenAI client wrapper with no-key and service-failure safety."""

from __future__ import annotations

from functools import lru_cache

from config import LLM_TIMEOUT_SECONDS, OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL


class LLMUnavailableError(RuntimeError):
    """Raised when an optional model response cannot be obtained safely."""


def is_configured() -> bool:
    """Return whether an API key was supplied through the environment."""
    return bool(OPENAI_API_KEY)


@lru_cache(maxsize=1)
def _client():
    if not is_configured():
        raise LLMUnavailableError("No LLM API key is configured.")
    try:
        from openai import OpenAI

        options = {"api_key": OPENAI_API_KEY, "timeout": LLM_TIMEOUT_SECONDS}
        if OPENAI_BASE_URL:
            options["base_url"] = OPENAI_BASE_URL
        return OpenAI(**options)
    except Exception as exc:
        raise LLMUnavailableError("The LLM client could not be initialized.") from exc


def generate_text(system_prompt: str, user_prompt: str) -> str:
    """Generate a concise response without logging any resume data or API credentials."""
    try:
        completion = _client().chat.completions.create(
            model=OPENAI_MODEL,
            temperature=0.2,
            max_tokens=1300,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        content = completion.choices[0].message.content
        if not content:
            raise LLMUnavailableError("The LLM returned an empty response.")
        return content.strip()
    except LLMUnavailableError:
        raise
    except Exception as exc:
        raise LLMUnavailableError("The optional AI service is unavailable. Rule-based guidance is still available.") from exc
