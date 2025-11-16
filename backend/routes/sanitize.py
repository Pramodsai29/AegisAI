from flask import Blueprint, request, jsonify
from utils.sanitizer import sanitize_text
from utils.risk import compute_risk
from utils.logger import add_log
import re

sanitize_bp = Blueprint('sanitize', __name__, url_prefix='/api')

@sanitize_bp.post('/sanitize')
def sanitize_route():
    """PII sanitization + context + risk scoring.
    Input: { "input": "text" }
    Output: {
      sanitized: str,
      entities: [{entity, label}],
      context: str,
      confidence: float,
      risk_score: int,
      rehydration_map: dict
    }
    """
    data = request.get_json(silent=True) or {}
    text = data.get('input', '') or ''
    # Note: Currency is now handled in sanitize_text with placeholder system
    # Force spaCy-only backend regardless of request parameter
    ner = 'spacy'

    sanitized, entities, context, confidence, rehydration_map, entities_summary = sanitize_text(text, ner=ner)
    # Compute risk - ensure it's always an integer between 0-100
    try:
        risk_score = compute_risk(entities, context)
        risk_score = int(max(0, min(100, risk_score)))  # Ensure it's 0-100 integer
    except Exception as e:
        print(f"[Sanitize Route] Risk computation failed: {repr(e)}")
        # Fallback: compute basic risk from entity count
        risk_score = min(100, len(entities) * 10) if entities else 0

    # Log entry - NEVER log the rehydration_map, original PII, or input text
    # Only log metadata and sanitized content
    add_log({
        'stage': 'sanitize',
        'input_length': len(text) if text else 0,  # Only length, not content
        'sanitized_length': len(sanitized) if sanitized else 0,  # Only length, not content
        'entities_count': len(entities) if entities else 0,  # Only count, not actual entities
        'context': context,
        'confidence': confidence,
        'risk': risk_score,
        'ner': ner or 'auto',
        # DO NOT log: input text, sanitized text content, entities details, rehydration_map, or any PII
    })

    return jsonify({
        'sanitized': sanitized,
        'sanitized_text': sanitized,  # Alias for compatibility
        'entities': entities,
        'entities_summary': entities_summary,  # New format with placeholders
        'context': context,
        'confidence': confidence,
        'risk_score': risk_score,
        'risk': risk_score,
        'ner': ner or 'auto',
        'rehydration_map': rehydration_map,  # Pass through for ephemeral use only
    })
