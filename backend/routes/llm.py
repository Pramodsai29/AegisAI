from flask import Blueprint, request, jsonify
from utils.logger import add_log
from utils.llm_client import call_llm
import re

llm_bp = Blueprint('llm', __name__, url_prefix='/api')

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


@llm_bp.post('/llm')
def llm_route():
    """Generate a safe LLM-like response using sanitized text and context.
    Input: { sanitized: str, context: { category: str, confidence: number }, rehydration_map?: dict }
    Output: { 
        answer: str,
        confidence: float,
        explanations: str,
        fallback_used: bool,
        raw: str,
        rehydration_map?: dict
    }
    
    NOTE: rehydration_map is passed through but NEVER used or sent to LLM.
    Only sanitized_text goes to the LLM via llm_client.
    """
    data = request.get_json(silent=True) or {}
    sanitized = data.get('sanitized') or ''
    context = data.get('context') or {}
    rehydration_map = data.get('rehydration_map') or {}  # Accept but don't use

    # Call LLM client with robust placeholder preservation
    llm_result = call_llm(sanitized, context, retry_on_failure=True)

    # Log entry - NEVER log rehydration_map or original PII
    add_log({
        'stage': 'llm',
        'context': context,
        'output_length': len(llm_result.get('answer', '')),
        'fallback_used': llm_result.get('fallback_used', False),
        'confidence': llm_result.get('confidence', 0.0),
        # DO NOT log rehydration_map or answer content
    })

    # Get the raw LLM answer (may contain placeholders)
    raw_answer = llm_result.get('answer', '')
    
    # Replace placeholders with generic terms for user-facing output
    # This makes the response natural and readable without exposing sensitive data
    natural_answer = replace_placeholders_with_generic_terms(raw_answer) if raw_answer else ""
    
    # Return LLM result with natural language (no placeholders)
    response = {
        'answer': natural_answer,  # Natural language, no placeholders
        'confidence': llm_result.get('confidence', 0.0),
        'explanations': llm_result.get('explanations', ''),
        'fallback_used': llm_result.get('fallback_used', False),
        'raw': raw_answer,  # Keep raw for internal processing if needed
        'rehydration_map': rehydration_map,  # Pass through ephemerally (will be deleted)
    }
    
    # Backward compatibility
    response['output'] = natural_answer
    response['provider'] = 'gemini' if not llm_result.get('fallback_used', True) else 'fallback'

    return jsonify(response)
