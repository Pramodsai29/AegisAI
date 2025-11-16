from flask import Blueprint, request, jsonify
from utils.logger import add_log
from utils.guardrails_wrapper import run_output_guardrails
import re

output_filter_bp = Blueprint('output_filter', __name__, url_prefix='/api')

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+", re.I)
PHONE_RE = re.compile(r"(\+?\d[\d\s\-]{7,}\d)")
ID_RE = re.compile(r"\b(\d{4}[-\s]?){3,}\d{4}\b")

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


@output_filter_bp.post('/output-filter')
def output_filter_route():
    """Post-process the LLM response to ensure privacy safety.
    Input: { 
        llm_output: dict (with 'answer' and/or 'raw' keys), OR
        answer: str (backward compat),
        sanitized: str, 
        context?: dict, 
        rehydration_map?: dict 
    }
    Output: { 
        safe_sanitized_text: str, 
        leak_detected: bool, 
        notes: str or None
    }
    
    IMPORTANT: This works on SANITIZED content (with placeholders), NOT rehydrated.
    Uses NER detector to check for actual PII leaks.
    """
    data = request.get_json(silent=True) or {}
    
    # Extract text from llm_output dict or fallback to answer string (backward compat)
    # Frontend sends 'answer' as string, so prioritize that
    text_to_check = data.get('answer') or data.get('original') or ""
    
    # Also check if llm_output dict was sent
    llm_output = data.get('llm_output') or {}
    if isinstance(llm_output, dict) and not text_to_check:
        text_to_check = llm_output.get("answer") or llm_output.get("raw") or ""
    
    # Ensure we have text to process
    if not text_to_check:
        # If no text provided, return empty but valid structure
        return jsonify({
            'safe_sanitized_text': "",
            'leak_detected': False,
            'notes': None
        })
    
    # STEP 1: Run NVIDIA Guardrails on the LLM output (with placeholders)
    # This ensures the output is safe and compliant with privacy policies
    sanitized_input = data.get('sanitized') or ''
    context = data.get('context') or {}
    
    guarded_text = run_output_guardrails(
        text_to_check,  # LLM output with placeholders
        {
            **context,
            'sanitized_preview': (sanitized_input[:200] if isinstance(sanitized_input, str) else ''),
        },
    )
    
    # Ensure guarded_text is valid
    if not guarded_text or not isinstance(guarded_text, str):
        guarded_text = text_to_check  # Fallback to original if guardrails fails
    
    # STEP 2: Use sanitizer's NER to detect if any actual PII leaked (not placeholders)
    from utils.sanitizer import sanitize_text
    
    leak_detected = False
    
    # Run sanitizer on the guarded text to detect any PII
    # If it finds entities, that means actual PII leaked (not placeholders)
    try:
        check_sanitized, check_entities, _, _, _, _ = sanitize_text(guarded_text, ner='spacy')
        # If entities were found, check if they're actual PII (not placeholders)
        if check_entities:
            placeholder_pattern = re.compile(r'\[\[[A-Z_]+\d+\]\]')
            for entity in check_entities:
                entity_text = entity.get('entity', '')
                # If entity is not a placeholder, it's a leak
                if not placeholder_pattern.match(entity_text):
                    leak_detected = True
                    break
    except Exception as e:
        # If sanitizer fails, be conservative and check with regex
        print(f"[Output Filter] Sanitizer check failed: {repr(e)}")
        # Fallback regex check
        placeholder_pattern = re.compile(r'\[\[[A-Z_]+\d+\]\]')
        if EMAIL_RE.search(guarded_text) or PHONE_RE.search(guarded_text):
            matches = EMAIL_RE.findall(guarded_text) + PHONE_RE.findall(guarded_text)
            for match in matches:
                if not placeholder_pattern.match(match):
                    leak_detected = True
                    break
    
    # STEP 3: Apply additional regex-based scrubbing as final safety layer
    filtered_text = guarded_text
    # Only mask actual PII patterns (not placeholders)
    placeholder_pattern = re.compile(r'\[\[[A-Z_]+\d+\]\]')
    
    # Check for email leaks (not placeholders)
    email_matches = EMAIL_RE.findall(filtered_text)
    for email in email_matches:
        if not placeholder_pattern.match(email):
            filtered_text = EMAIL_RE.sub('[EMAIL_MASKED]', filtered_text)
            leak_detected = True
            break
    
    # Check for phone leaks (not placeholders)
    phone_matches = PHONE_RE.findall(filtered_text)
    for phone in phone_matches:
        if not placeholder_pattern.match(phone):
            filtered_text = PHONE_RE.sub('[PHONE_MASKED]', filtered_text)
            leak_detected = True
            break
    
    # STEP 4: Replace placeholders with generic, natural terms
    # This makes the output readable without exposing sensitive data
    if leak_detected:
        safe_sanitized_text = "We cannot provide this due to sensitive data concerns."
        notes = "sensitive_entity_detected"
    else:
        # Replace placeholders with natural language terms
        safe_sanitized_text = replace_placeholders_with_generic_terms(filtered_text)
        notes = None
    
    # Log entry - NEVER log sensitive data or text content
    # Only log metadata
    add_log({
        'stage': 'output_filter',
        'text_length': len(text_to_check) if text_to_check else 0,  # Only length, not content
        'leak_detected': leak_detected,
        'guardrails_applied': True,  # Indicate guardrails was used
        # DO NOT log: text content, rehydration_map, or any sensitive data
    })

    return jsonify({
        'safe_sanitized_text': safe_sanitized_text,
        'leak_detected': leak_detected,
        'notes': notes
    })
