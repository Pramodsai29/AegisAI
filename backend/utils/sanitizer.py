import re
from typing import List, Tuple, Dict
from utils.logger import add_log

try:
    import spacy
    try:
        # Try the transformer model first
        _NLP = spacy.load("en_core_web_trf")
    except Exception:
        # Fallback to small model if transformer not available
        _NLP = spacy.load("en_core_web_sm")
except Exception:
    _NLP = None

# Enhanced regex patterns for comprehensive PII detection
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+", re.I)
# Phone: Match phone numbers with country codes or 10-digit numbers
# Format: +XX XXXX XXXXX or +XX XXX-XXX-XXXX or XXX-XXX-XXXX or 10 digits standalone
# Handle spaces in international format: +91 98765 43210 (country code + space + number with spaces)
# Handle US format: +1 555-123-4567 (country code + space + XXX-XXX-XXXX)
# Order matters: more specific patterns first
PHONE_RE = re.compile(r"(\+\d{1,4}\s\d{3}[\s\-]?\d{3}[\s\-]?\d{4}(?!\d))|(\+\d{1,4}[\s\-]\d{3,}[\s\-]?\d{3,}(?!\d))|(\+\d{1,4}[\s\-]?\d{3}[\s\-]?\d{3}[\s\-]?\d{4}(?!\d))|(\b\d{3}[\s\-]?\d{3}[\s\-]?\d{4}\b)|(\b\d{10}\b(?!\d))")
# ID: Generic ID pattern (but check after specific patterns to avoid false positives)
# Only match if it's not already matched as card/aadhaar/account
ID_RE = re.compile(r"\b(\d{4}[-\s]?){3,}\d{1,4}\b")
# PAN: 5 letters, 4 digits, 1 letter (e.g., ABCDE1234F)
PAN_RE = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b", re.I)
# Aadhaar: exactly 12 digits, optionally with spaces or hyphens (4-4-4 pattern)
# Must be exactly 12 digits total, not 16 (which would be a card)
AADHAAR_RE = re.compile(r"\b(?<!\d)\d{4}[-\s]?\d{4}[-\s]?\d{4}(?!\d)\b")
# Credit/Debit Card: 13-19 digits, typically 16 digits in groups of 4
# Must be 13-19 digits total, and if it's 16 digits, it's likely a card
CARD_RE = re.compile(r"\b(?:\d{4}[-\s]?){3,4}\d{1,4}\b")
# Account numbers: 9-18 digits, continuous (no separators), and NOT matching phone patterns
# Account numbers typically don't follow the 4-4-4-4 pattern and are continuous digits
# Must NOT start with + (which would be a phone), and must NOT have separators like - or spaces
ACC_RE = re.compile(r"\b(?<!\+)(?<!\d)\d{9,18}(?!\d)\b")
# IP Address (valid IP range)
IP_RE = re.compile(r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b")
# URL
URL_RE = re.compile(r"https?://[^\s]+", re.I)
# SSN (US format)
SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
# Name pattern: Capitalized words that could be names (fallback if spaCy misses)
# Matches: "John Doe", "Mary Jane Smith", etc. (2-3 capitalized words)
NAME_RE = re.compile(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2}\b")
# Currency amounts (already handled in sanitize.py but we'll track them)
CURRENCY_RE = re.compile(r"(?:₹|Rs\.?|INR|\$|£|€)\s?\d+(?:[.,]\d{2})?", re.I)

CATEGORY_KEYWORDS = {
    "medical": ["diagnosis", "patient", "hospital", "medication", "doctor", "symptom", "clinic"],
    "financial": ["credit", "debit", "bank", "account", "loan", "salary", "invoice", "card"],
    "personal": ["address", "phone", "email", "ssn", "passport", "license", "birthday"],
}

LABEL_MAP = {
    "PERSON": "PERSON",
    "ORG": "ORG",
    "GPE": "LOCATION",
    "LOC": "LOCATION",
    "NORP": "GROUP",
    "FAC": "LOCATION",
    "DATE": "DATE",
    "TIME": "TIME",
    "MONEY": "MONEY",
    "CARDINAL": "NUMBER",
    "QUANTITY": "NUMBER",
    "ORDINAL": "NUMBER",
}


def _ensure_spacy():
    global _NLP
    if _NLP is None:
        try:
            import spacy  # type: ignore
            try:
                _NLP = spacy.load("en_core_web_trf")
            except Exception:
                _NLP = spacy.load("en_core_web_sm")
        except Exception:
            _NLP = None


def _simple_context_classify(text: str) -> Tuple[str, float]:
    t = (text or "").lower()
    scores = {k: 0 for k in CATEGORY_KEYWORDS.keys()}
    for cat, words in CATEGORY_KEYWORDS.items():
        for w in words:
            if w in t:
                scores[cat] += 1
    if not any(scores.values()):
        return "general", 0.5
    best = max(scores, key=scores.get)
    total = sum(scores.values()) or 1
    conf = min(0.95, max(0.55, scores[best] / total))
    return best, conf


def _context_classify_multi(text: str) -> Tuple[str, float, List[str]]:
    t = (text or "").lower()
    scores = {k: 0 for k in CATEGORY_KEYWORDS.keys()}
    for cat, words in CATEGORY_KEYWORDS.items():
        for w in words:
            if w in t:
                scores[cat] += 1
    if not any(scores.values()):
        return "general", 0.5, ["general"]
    ordered = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    ordered = [c for c, s in ordered if s > 0]
    combined = "-".join(ordered[:2]) if len(ordered) > 1 else ordered[0]
    best = ordered[0]
    total = sum(scores.values()) or 1
    best_score = scores[best] / total
    conf = min(0.95, max(0.55, best_score))
    return combined, conf, ordered

def sanitize_text(text: str, ner: str = None) -> Tuple[str, List[Dict], str, float, Dict[str, str]]:
    """
    Returns: sanitized_text, entities, context(str), confidence(float), rehydration_map
    entities = [{"entity": original_text, "label": label}]
    rehydration_map = {"[[PLACEHOLDER]]": "original_value"}
    """
    entities: List[Dict] = []
    spans: List[Tuple[int, int, str, str]] = []  # (start, end, label, original_text)
    rehydration_map: Dict[str, str] = {}
    placeholder_counters: Dict[str, int] = {}

    # Force spaCy-only behavior regardless of ner parameter
    backend = "spacy"
    _ensure_spacy()
    use_spacy = _NLP is not None

    def get_placeholder(label: str, original: str) -> str:
        """Generate unique numbered placeholder for an entity."""
        label_upper = label.upper()
        if label_upper not in placeholder_counters:
            placeholder_counters[label_upper] = 0
        placeholder_counters[label_upper] += 1
        placeholder = f"[[{label_upper}_{placeholder_counters[label_upper]}]]"
        rehydration_map[placeholder] = original
        return placeholder

    spacy_count = 0
    spacy_person_spans = set()  # Track spaCy-detected PERSON entities to avoid duplicate name detection
    
    if use_spacy:
        doc = _NLP(text)
        for ent in doc.ents:
            label = LABEL_MAP.get(ent.label_, ent.label_)
            original_text = ent.text
            # Mask ALL sensitive entities: PERSON (names), ORG, LOCATION, MONEY, DATE, etc.
            # Be comprehensive - mask anything that could be PII
            sensitive_labels = ["PERSON", "ORG", "LOCATION", "MONEY", "DATE", "TIME", "NUMBER", "GROUP"]
            if label in sensitive_labels:
                spans.append((ent.start_char, ent.end_char, label, original_text))
                entities.append({"entity": original_text, "label": label})
                spacy_count += 1
                # Track PERSON entities to avoid duplicate detection
                if label == "PERSON":
                    spacy_person_spans.add((ent.start_char, ent.end_char))

    # Enhanced regex-based detection for all PII types
    # Order matters: more specific patterns first to avoid false positives
    # Process numbers in order: Cards (16 with separators) -> Aadhaar (12) -> Phones (with + or separators) -> Accounts (continuous) -> Generic ID
    regex_patterns = [
        (PAN_RE, "PAN"),
        (SSN_RE, "SSN"),
        (EMAIL_RE, "EMAIL"),
        (IP_RE, "IP"),
        (URL_RE, "URL"),
        (CURRENCY_RE, "CURRENCY"),  # Currency amounts
        (CARD_RE, "CARD"),  # Check cards FIRST (13-19 digits, typically 16 with separators)
        (AADHAAR_RE, "AADHAAR"),  # Check Aadhaar after cards (exactly 12 digits)
        (PHONE_RE, "PHONE"),  # Check phones BEFORE accounts (phones have + or separators)
        (ACC_RE, "ACC"),  # Account numbers (9-18 digits, continuous, no separators) - checked AFTER phones
        (ID_RE, "ID"),  # Generic ID pattern last (to catch anything else)
    ]

    for pattern, label in regex_patterns:
        for m in pattern.finditer(text):
            original_text = m.group(0)
            # Check if this span overlaps with existing spans
            overlap = False
            for existing_start, existing_end, _, _ in spans:
                if not (m.end() <= existing_start or m.start() >= existing_end):
                    overlap = True
                    break
            if not overlap:
                # Post-process to distinguish between similar numeric patterns
                digits_only = re.sub(r'[-\s\+]', '', original_text)
                digit_count = len(digits_only)
                
                # Refine label based on digit count and pattern
                # Check CARD first since it's checked before AADHAAR in patterns
                if label == "CARD":
                    if digit_count < 13 or digit_count > 19:
                        # Not actually a card (must be 13-19 digits)
                        # Could be an account number if continuous
                        if 9 <= digit_count <= 18 and not re.search(r'[-\s]', original_text):
                            label = "ACC"  # Reclassify as account number
                        else:
                            continue
                    elif digit_count == 16:
                        # 16 digits: check if it has separators (card) or not (account)
                        if ' ' in original_text or '-' in original_text:
                            # Has separators, definitely a card
                            pass
                        else:
                            # No separators, more likely an account number
                            label = "ACC"  # Reclassify as account
                    # For other card lengths (13-15, 17-19), keep as CARD
                elif label == "AADHAAR":
                    if digit_count != 12:
                        # Not actually an Aadhaar (must be exactly 12 digits)
                        continue
                    # Additional check: if it's part of a longer sequence that looks like a card, skip
                    # This is handled by checking CARD pattern first
                elif label == "ACC":
                    if digit_count < 9 or digit_count > 18:
                        # Not actually an account number
                        continue
                    # Account numbers should NOT have separators or start with +
                    # If it has separators or +, it was already caught by PHONE or CARD pattern
                    if re.search(r'[-\s\+]', original_text):
                        # Has separators or +, it's NOT an account number
                        # This should have been caught by PHONE or CARD pattern already
                        # Skip it - it's not an account number
                        continue
                    # Additional check: if it's exactly 10 digits with no separators,
                    # it could be a phone number, but since PHONE pattern was checked first
                    # and didn't catch it (no separators, no +), it's likely an account number
                    # Account numbers are continuous digits, no separators, no +
                    # This is the correct pattern for account numbers
                elif label == "PHONE":
                    # Phone numbers should be 10+ digits, but not match card/aadhaar patterns
                    # Allow up to 15 digits for international numbers (country code + number)
                    if digit_count > 15:
                        # Too long, likely not a phone, skip
                        continue
                    if digit_count < 10:
                        # Too short, skip
                        continue
                    # If it's 12 digits and has separators, might be aadhaar - but if it starts with +, it's a phone
                    if digit_count == 12 and not original_text.startswith('+'):
                        # Could be aadhaar, skip
                        continue
                    # CRITICAL: Distinguish between phone and account numbers
                    # Phone numbers: typically have separators (-, spaces), start with +, OR are exactly 10 digits
                    # Account numbers: 9-18 digits, continuous, no separators, no +, typically longer (12+ digits)
                    if not re.search(r'[-\s\+]', original_text):
                        # No separators and no + - check if it's likely a phone or account
                        if digit_count == 10:
                            # Exactly 10 digits without separators = likely phone number (US/India format)
                            # Keep as PHONE
                            pass
                        elif 9 <= digit_count <= 11:
                            # 9-11 digits without separators could be phone, but ambiguous
                            # Check context - if nearby words suggest "account", skip
                            # For now, keep as PHONE (phones are more common in this range)
                            pass
                        elif digit_count >= 12:
                            # 12+ digits without separators = likely account number, not phone
                            # Skip - let ACC pattern catch it
                            continue
                        else:
                            # 9-11 digits, ambiguous - prefer phone for shorter numbers
                            pass
                elif label == "ID":
                    # ID pattern should not match things already classified as cards/accounts
                    if digit_count >= 9:
                        # Could be account or card, skip (should have been caught earlier)
                        continue
                
                spans.append((m.start(), m.end(), label, original_text))
                entities.append({"entity": original_text, "label": label})
    
    # Fallback name detection: Use regex if spaCy missed names
    # Only check if spaCy is not available or if we want to catch names spaCy missed
    if not use_spacy or True:  # Always run as fallback
        for m in NAME_RE.finditer(text):
            original_text = m.group(0)
            # Check if this overlaps with existing spans (especially spaCy PERSON)
            overlap = False
            for existing_start, existing_end, _, _ in spans:
                if not (m.end() <= existing_start or m.start() >= existing_end):
                    overlap = True
                    break
            # Also check if spaCy already detected this as PERSON
            is_spacy_person = False
            for spacy_start, spacy_end in spacy_person_spans:
                if not (m.end() <= spacy_start or m.start() >= spacy_end):
                    is_spacy_person = True
                    break
            # Only add if no overlap and not already detected by spaCy
            if not overlap and not is_spacy_person:
                # Additional check: make sure it's not a common word or location
                # Skip if it's a single word (likely not a name) or common words
                words = original_text.split()
                if len(words) >= 2:  # At least first and last name
                    # Skip common titles and words
                    skip_words = {'The', 'A', 'An', 'This', 'That', 'New', 'Old', 'North', 'South', 'East', 'West', 
                                 'United', 'States', 'Kingdom', 'Republic', 'City', 'Street', 'Avenue', 'Road'}
                    if not any(w in skip_words for w in words):
                        spans.append((m.start(), m.end(), "PERSON", original_text))
                        entities.append({"entity": original_text, "label": "PERSON"})

    # Merge overlapping spans prefer longer
    spans = sorted(spans, key=lambda s: (s[0], -(s[1]-s[0])))
    merged = []
    for s in spans:
        if not merged or s[0] > merged[-1][1]:
            merged.append(list(s))
        else:
            # overlap - keep the longer span
            if s[1] > merged[-1][1]:
                merged[-1] = list(s)
            # keep first label if same length
    spans = [(a, b, c, d) for a, b, c, d in merged]

    # Build sanitized text with unique numbered placeholders
    out = []
    last = 0
    for start, end, label, original_text in spans:
        if start < last:
            continue
        out.append(text[last:start])
        placeholder = get_placeholder(label, original_text)
        out.append(placeholder)
        last = end
    out.append(text[last:])
    sanitized = "".join(out)

    # Context classification
    context, conf, _ = _context_classify_multi(text)

    seen = set()
    dedup = []
    entities_summary = []  # Build entities_summary with placeholder info
    
    for e in entities:
        key = (e.get("entity"), e.get("label"))
        if key in seen:
            continue
        seen.add(key)
        dedup.append(e)
        
        # Find the placeholder for this entity
        entity_text = e.get("entity")
        entity_label = e.get("label")
        placeholder = None
        for ph, orig in rehydration_map.items():
            if orig == entity_text:
                placeholder = ph
                break
        
        # Build entities_summary entry
        entities_summary.append({
            "type": entity_label,
            "placeholder": placeholder or f"[[{entity_label}_UNKNOWN]]",
            "confidence": 0.98,  # High confidence for detected entities
            "entity": entity_text  # Original entity text (for reference, not logged)
        })

    try:
        add_log({
            'stage': 'sanitize_debug',
            'backend': backend,
            'use_spacy': bool(use_spacy),
            'spacy_entities': spacy_count,
            'total_entities': len(dedup),
            # DO NOT log rehydration_map or entity values
        })
    except Exception:
        pass

    return sanitized, dedup, context, float(conf), rehydration_map, entities_summary
