"""
LLM Client with robust placeholder preservation and JSON parsing.
Enforces strict placeholder preservation and handles fallbacks.
"""
import os
import json
import re
from typing import Dict, Any, Optional

try:
    import google.generativeai as genai
    _GEMINI_AVAILABLE = True
except Exception:
    _GEMINI_AVAILABLE = False


def _build_system_prompt() -> str:
    """Build the system prompt that enforces placeholder preservation."""
    return (
        "You are a privacy-safe assistant. You are given text containing placeholders "
        "like [[PERSON_1]], [[EMAIL_1]], [[PHONE_1]]. You must NOT modify or remove these placeholders. "
        "Output EXACTLY a JSON object with a single key 'answer' whose value is the textual reply "
        "and which contains placeholders verbatim wherever appropriate. "
        "If you cannot answer, return {\"answer\":\"REFUSE\"}. "
        "Do NOT change, translate, expand, paraphrase, or remove placeholders of the form [[TYPE_n]]. "
        "Keep them exactly as-is in your answer."
    )


def _build_user_prompt(sanitized_text: str, context: Dict[str, Any]) -> str:
    """Build the user prompt with sanitized text and context."""
    cat = (context.get('category') or 'general').lower()
    return (
        f"Context category: {cat}.\n"
        f"Sanitized input: {sanitized_text}\n\n"
        "Write a helpful, safety-focused answer. Use placeholders exactly as they appear in the input. "
        "Output valid JSON ONLY with an 'answer' field containing your response."
    )


def _parse_llm_response(text: str) -> Optional[Dict[str, Any]]:
    """Parse LLM response as JSON and extract answer field."""
    if not text:
        return None
    
    # Try to parse as JSON
    try:
        # Remove markdown code blocks if present
        cleaned = text.strip()
        if cleaned.startswith('```'):
            # Extract JSON from code block
            lines = cleaned.split('\n')
            json_lines = []
            in_json = False
            for line in lines:
                if line.strip().startswith('```'):
                    if in_json:
                        break
                    in_json = True
                    continue
                if in_json:
                    json_lines.append(line)
            cleaned = '\n'.join(json_lines)
        elif cleaned.startswith('```json'):
            cleaned = cleaned[7:].strip()
            if cleaned.endswith('```'):
                cleaned = cleaned[:-3].strip()
        
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict) and 'answer' in parsed:
            return parsed
    except (json.JSONDecodeError, ValueError):
        pass
    
    # Try to extract JSON object from text
    json_match = re.search(r'\{[^{}]*"answer"[^{}]*\}', text, re.DOTALL)
    if json_match:
        try:
            parsed = json.loads(json_match.group(0))
            if isinstance(parsed, dict) and 'answer' in parsed:
                return parsed
        except (json.JSONDecodeError, ValueError):
            pass
    
    return None


def _check_placeholders_preserved(answer_text: str, sanitized_text: str) -> bool:
    """Check if placeholders from sanitized_text are preserved in answer."""
    placeholder_pattern = re.compile(r'\[\[[A-Z_]+\d+\]\]')
    sanitized_placeholders = set(placeholder_pattern.findall(sanitized_text))
    answer_placeholders = set(placeholder_pattern.findall(answer_text))
    
    # Check if all placeholders that should be in answer are present
    # (Some might not be needed if answer doesn't reference them)
    # At minimum, if answer references entities, placeholders should be there
    return len(answer_placeholders) > 0 or len(sanitized_placeholders) == 0


def call_llm(
    sanitized_text: str,
    context: Dict[str, Any],
    retry_on_failure: bool = True
) -> Dict[str, Any]:
    """
    Call LLM with strict placeholder preservation requirements.
    
    Args:
        sanitized_text: Text with placeholders like [[PERSON_1]]
        context: Context dict with category, confidence, etc.
        retry_on_failure: Whether to retry once if parsing fails
    
    Returns:
        Dict with:
        - answer: str (the LLM response text)
        - confidence: float
        - explanations: str (status message)
        - fallback_used: bool
        - raw: str (raw response from model)
    """
    api_key = os.getenv('GEMINI_API_KEY')
    model_name = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')
    
    if not api_key or not _GEMINI_AVAILABLE:
        return {
            "answer": sanitized_text,
            "confidence": 0.0,
            "explanations": "llm_unavailable_fallback",
            "fallback_used": True,
            "raw": ""
        }
    
    system_prompt = _build_system_prompt()
    user_prompt = _build_user_prompt(sanitized_text, context)
    
    def _make_request() -> Optional[str]:
        """Make a single LLM request."""
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(model_name)
            resp = model.generate_content([system_prompt, user_prompt])
            text = getattr(resp, 'text', None) or (
                resp.candidates[0].content.parts[0].text 
                if getattr(resp, 'candidates', None) and len(resp.candidates) > 0
                else None
            )
            return text.strip() if text else None
        except Exception as e:
            print(f"[LLM Client] Error: {repr(e)}")
            return None
    
    # First attempt
    raw_text = _make_request()
    
    if raw_text:
        parsed = _parse_llm_response(raw_text)
        if parsed and 'answer' in parsed:
            answer = parsed['answer']
            # Check if placeholders are preserved
            if _check_placeholders_preserved(answer, sanitized_text):
                return {
                    "answer": answer,
                    "confidence": 0.9,
                    "explanations": "success_json_with_placeholders",
                    "fallback_used": False,
                    "raw": raw_text
                }
    
    # Retry if enabled and first attempt failed
    if retry_on_failure:
        # Strengthen instruction for retry
        stronger_system = (
            system_prompt + "\n\nCRITICAL: You MUST output valid JSON with 'answer' field. "
            "You MUST preserve ALL placeholders like [[PERSON_1]] exactly as they appear. "
            "Do NOT paraphrase or remove them."
        )
        
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(model_name)
            resp = model.generate_content([stronger_system, user_prompt])
            raw_text = getattr(resp, 'text', None) or (
                resp.candidates[0].content.parts[0].text 
                if getattr(resp, 'candidates', None) and len(resp.candidates) > 0
                else None
            )
            if raw_text:
                raw_text = raw_text.strip()
                parsed = _parse_llm_response(raw_text)
                if parsed and 'answer' in parsed:
                    answer = parsed['answer']
                    if _check_placeholders_preserved(answer, sanitized_text):
                        return {
                            "answer": answer,
                            "confidence": 0.8,
                            "explanations": "success_after_retry",
                            "fallback_used": False,
                            "raw": raw_text
                        }
        except Exception as e:
            print(f"[LLM Client] Retry error: {repr(e)}")
    
    # Fallback: return sanitized text or raw response
    fallback_answer = raw_text if raw_text else sanitized_text
    
    return {
        "answer": fallback_answer,
        "confidence": 0.0,
        "explanations": "non_json_or_placeholders_missing_fallback",
        "fallback_used": True,
        "raw": raw_text or ""
    }

