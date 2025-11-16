import os
import json
from typing import Any, Dict, Optional

try:  # Optional dependency
    from nemoguardrails import LLMRails
    from nemoguardrails.config import RailsConfig
    _NEMO_AVAILABLE = True
except Exception:  # pragma: no cover - best-effort import
    LLMRails = None  # type: ignore
    RailsConfig = None  # type: ignore
    _NEMO_AVAILABLE = False


# Lazily-initialized global rails instance
_rails: Optional["LLMRails"] = None


def _get_config_path() -> str:
    """Return the NeMo Guardrails config directory.

    By default we look for `backend/guardrails`, but you can override this
    with the `NEMO_GUARDRAILS_CONFIG` environment variable.
    """
    env_path = os.getenv("NEMO_GUARDRAILS_CONFIG")
    if env_path:
        return env_path

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, "guardrails")


def _ensure_rails() -> None:
    """Initialize the global rails instance if possible.

    If NeMo Guardrails is not installed or config is missing/broken,
    we fall back gracefully by keeping `_rails` as None.
    """
    global _rails

    if _rails is not None or not _NEMO_AVAILABLE:
        return

    try:
        config_path = _get_config_path()
        if not os.path.isdir(config_path):
            # No config directory present; skip guardrails.
            return

        rails_config = RailsConfig.from_path(config_path)  # type: ignore[arg-type]
        _rails = LLMRails(rails_config)  # type: ignore[call-arg]
    except Exception as e:  # pragma: no cover - defensive
        # If anything goes wrong, we simply disable guardrails.
        print("[NeMo Guardrails] Initialization error:", repr(e))
        _rails = None


def run_output_guardrails(text: str, context: Optional[Dict[str, Any]] = None) -> str:
    """Run the LLM output through NeMo Guardrails if available.

    Args:
        text: The LLM-generated response to be checked/rewritten.
        context: Optional extra info (e.g., category, risk_score) that
                 can be used in your NeMo rail definitions as variables.

    Returns:
        A potentially rewritten, safer version of `text`. If Guardrails is
        unavailable or fails, returns the original `text`.
    """
    if not text:
        return text

    _ensure_rails()
    if _rails is None:
        return text

    try:
        # We treat the existing LLM response as an assistant message and
        # optionally pass context as a separate message. You can adapt this
        # to match your NeMo rail design.
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a safety filter that reviews and, if needed, "
                    "rewrites the assistant's response to ensure it is "
                    "privacy-preserving and compliant with safety policies."
                ),
            },
            {"role": "assistant", "content": text},
        ]

        if context:
            messages.append(
                {
                    "role": "user",
                    "content": f"Context metadata: {json.dumps(context)}",
                }
            )

        # Depending on your NeMo Guardrails config, this may return a string
        # or a more complex structure. We handle the common string case and
        # fall back to the original text otherwise.
        # Use the LLMRails.generate method which processes through the output rails
        result = _rails.generate(messages=messages)  # type: ignore[call-arg]

        if isinstance(result, str):
            cleaned = result.strip()
            return cleaned or text

        if isinstance(result, dict):
            candidate = (
                result.get("output")
                or result.get("response")
                or result.get("content")
                or result.get("messages", [{}])[-1].get("content", "")
            )
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()
            # Check if result has messages array
            if isinstance(result.get("messages"), list) and len(result.get("messages", [])) > 0:
                last_msg = result["messages"][-1]
                if isinstance(last_msg, dict) and "content" in last_msg:
                    content = last_msg["content"]
                    if isinstance(content, str) and content.strip():
                        return content.strip()

        return text

    except Exception as e:  # pragma: no cover - defensive
        print("[NeMo Guardrails] Runtime error:", repr(e))
        return text
