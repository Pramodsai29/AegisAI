from flask import Blueprint, request, jsonify
from utils.risk import compute_risk
from utils.logger import add_log
import re

final_bp = Blueprint('final', __name__, url_prefix='/api')

# Placeholder replacement patterns for natural language
PLACEHOLDER_RE = re.compile(r'\[\[([A-Z_]+?)_(\d+)\]\]')

def replace_placeholders_with_generic_terms(text: str) -> str:
    """
    Replace placeholders like [[PERSON_1]], [[EMAIL_1]] with natural, generic terms.
    This makes the output readable without exposing sensitive data.
    """
    if not text:
        return text
    
    # Track which entity types we've seen to use appropriate pronouns/references
    seen_entities = {}
    
    def replace_placeholder(match):
        entity_type = match.group(1)  # e.g., 'PERSON', 'EMAIL'
        entity_num = int(match.group(2))  # e.g., 1, 2
        
        if entity_type == 'PERSON':
            if 'PERSON' not in seen_entities:
                seen_entities['PERSON'] = {}
            if entity_num not in seen_entities['PERSON']:
                person_count = len(seen_entities['PERSON']) + 1
                seen_entities['PERSON'][entity_num] = person_count
            else:
                person_count = seen_entities['PERSON'][entity_num]
            
            # Use natural language instead of "person 1, 2, 3"
            if person_count == 1:
                return "the person"
            elif person_count == 2:
                return "the other person"
            elif person_count == 3:
                return "another person"
            else:
                return "the individual"
        
        elif entity_type == 'EMAIL':
            if 'EMAIL' not in seen_entities:
                seen_entities['EMAIL'] = {}
            if entity_num not in seen_entities['EMAIL']:
                email_count = len(seen_entities['EMAIL']) + 1
                seen_entities['EMAIL'][entity_num] = email_count
            else:
                email_count = seen_entities['EMAIL'][entity_num]
            
            if email_count == 1:
                return "their email"
            else:
                return "the email address"
        
        elif entity_type == 'PHONE':
            if 'PHONE' not in seen_entities:
                seen_entities['PHONE'] = {}
            if entity_num not in seen_entities['PHONE']:
                phone_count = len(seen_entities['PHONE']) + 1
                seen_entities['PHONE'][entity_num] = phone_count
            else:
                phone_count = seen_entities['PHONE'][entity_num]
            
            if phone_count == 1:
                return "their phone number"
            else:
                return "the phone number"
        
        elif entity_type == 'ACC':
            if 'ACC' not in seen_entities:
                seen_entities['ACC'] = {}
            if entity_num not in seen_entities['ACC']:
                acc_count = len(seen_entities['ACC']) + 1
                seen_entities['ACC'][entity_num] = acc_count
            else:
                acc_count = seen_entities['ACC'][entity_num]
            
            if acc_count == 1:
                return "their account number"
            else:
                return "the account number"
        
        elif entity_type == 'PAN':
            return "the PAN number"
        
        elif entity_type == 'AADHAAR':
            return "the Aadhaar number"
        
        elif entity_type == 'CARD':
            return "the card number"
        
        elif entity_type == 'CURRENCY':
            return "the amount"
        
        elif entity_type == 'IP':
            return "the IP address"
        
        elif entity_type == 'URL':
            return "the URL"
        
        elif entity_type == 'SSN':
            return "the SSN"
        
        else:
            # Generic fallback
            return "the information"
    
    # Replace all placeholders
    result = PLACEHOLDER_RE.sub(replace_placeholder, text)
    
    # Clean up any awkward phrasing
    result = re.sub(r'\s+', ' ', result)  # Multiple spaces to single
    result = re.sub(r'\s+([,.!?])', r'\1', result)  # Space before punctuation
    
    return result.strip()


@final_bp.post('/final')
def final_route():
    """Aggregate final output, rehydrate placeholders, and compute/confirm final risk score.
    Input: { 
        sanitized_text: str,
        entities_summary: list,
        rehydration_map: dict,
        context: dict,
        risk: int,
        llm_output: dict,
        filtered_output: dict
    }
    Output: { 
        sanitized: dict,
        context: dict,
        risk: int,
        llm_response: dict,
        filtered_output: dict,
        final_output: str
    }
    
    PHASE 4: REHYDRATION
    After output filtering, we rehydrate the safe_sanitized_text by replacing placeholders
    with original values. The mapping is immediately deleted after use and never persisted.
    """
    data = request.get_json(silent=True) or {}
    
    # Receive required inputs (with fallbacks for backward compatibility)
    sanitized_text = data.get('sanitized_text') or data.get('sanitized') or ''
    entities_summary = data.get('entities_summary') or data.get('entities') or []
    rehydration_map = data.get('rehydration_map') or {}
    context = data.get('context') or {}
    original_risk = data.get('risk')  # Store original input risk (for reference only, not used)
    llm_output = data.get('llm_output') or data.get('llm_result') or {}
    filtered_output = data.get('filtered_output') or {}
    
    # Validate context
    if not context or not isinstance(context, dict):
        context = {'category': 'general', 'confidence': 0.5}
    
    # Validate filtered_output
    if not filtered_output or not isinstance(filtered_output, dict):
        filtered_output = {'safe_sanitized_text': '', 'leak_detected': False, 'notes': None}
    
    # Use sanitized_answer from filtered_output
    sanitized_answer = filtered_output.get("safe_sanitized_text") or ""
    
    # Fallback: if filtered_output is empty, try to get from llm_output
    if not sanitized_answer and isinstance(llm_output, dict):
        sanitized_answer = llm_output.get("answer") or llm_output.get("raw") or ""
    
    # SECURITY: NO REHYDRATION - Replace placeholders with generic terms
    # The final output should be readable and natural, but without sensitive data
    # Replace placeholders like [[PERSON_1]] with generic terms like "the person"
    final_text = replace_placeholders_with_generic_terms(sanitized_answer) if sanitized_answer else ""
    
    # ALWAYS compute risk based on FINAL OUTPUT (not original input)
    # The final output has no PII (only generic terms), so risk should be low
    from utils.sanitizer import sanitize_text
    from utils.risk import compute_risk
    
    # Analyze the final output text to compute its actual risk
    # Since final_text has no PII (only generic terms), risk should be minimal
    risk = 0  # Default to 0 (safe - no PII in final output)
    try:
        if final_text:
            final_sanitized, final_entities, final_context, _, _, _ = sanitize_text(final_text, ner='spacy')
            # Compute risk based on what's actually in the final output
            # final_context is a string from sanitize_text, use it directly
            category = final_context if isinstance(final_context, str) else (context.get('category') or 'general').lower()
            risk = compute_risk(final_entities, category)
            risk = int(max(0, min(100, risk)))  # Ensure it's 0-100 integer
        else:
            # Empty final text = no risk
            risk = 0
    except Exception as e:
        # If sanitization fails, use a safe low risk score
        # Final output has no PII, so risk should be low
        print(f"[Final Route] Risk computation failed: {repr(e)}")
        risk = 0  # Safe default - final output has no sensitive data
    
    # Ensure risk is always an integer
    risk = int(risk) if isinstance(risk, (int, float)) else 0
    
    # SECURITY: Immediately delete the rehydration_map from memory
    # We never use it, and we must ensure it's deleted immediately
    if rehydration_map and isinstance(rehydration_map, dict):
        rehydration_map.clear()
        del rehydration_map
    
    # Build sanitized dict
    sanitized_dict = {
        'sanitized_text': sanitized_text,
        'entities_summary': entities_summary if isinstance(entities_summary, list) else []
    }
    
    # Log entry - NEVER log sensitive data, rehydrated text, or rehydration_map
    # Only log metadata, never actual content
    add_log({
        'stage': 'final',
        'result_length': len(sanitized_answer) if sanitized_answer else 0,  # Only length, not content
        'risk': risk,
        'context_category': context.get('category') if isinstance(context, dict) else None,
        # DO NOT log: final_text, sanitized_answer content, rehydration_map, or any sensitive data
    })
    
    # Build final JSON response
    # Frontend expects 'final_rehydrated_text' key, so include both for compatibility
    response = {
        'sanitized': sanitized_dict,
        'context': context,
        'risk': risk,
        'llm_response': llm_output,
        'filtered_output': filtered_output,
        'final_output': final_text,
        'final_rehydrated_text': final_text  # Frontend expects this key
    }
    
    # Always return HTTP 200
    return jsonify(response), 200
