from flask import Blueprint, request, jsonify
from utils.sanitizer import _context_classify_multi
from utils.logger import add_log

context_bp = Blueprint('context', __name__, url_prefix='/api')


@context_bp.post('/context')
def context_route():
    """Contextual analysis of the input/sanitized text.
    Input: { input: str, sanitized: str }
    Output: { category: str, confidence: float }
    """
    data = request.get_json(silent=True) or {}
    text = data.get('input') or data.get('sanitized') or ''

    category, confidence, _ = _context_classify_multi(text)

    add_log({
        'stage': 'context',
        'category': category,
        'confidence': confidence,
    })

    return jsonify({
        'category': category,
        'confidence': confidence,
    })
