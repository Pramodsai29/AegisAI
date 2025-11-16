from typing import List, Dict

# Sensitivity weights (tunable)
ENTITY_WEIGHTS = {
    'EMAIL': 20,
    'PHONE': 20,
    'ID': 25,
    'PERSON': 15,
    'ORG': 10,
    'LOCATION': 10,
    'MONEY': 18,
    'DATE': 6,
    'TIME': 4,
    'NUMBER': 5,
    'GROUP': 8,
}

CONTEXT_MULTIPLIER = {
    'medical': 1.4,
    'financial': 1.4,
    'personal': 1.2,
    'general': 1.0,
}


def compute_risk(entities: List[Dict], context: str) -> int:
    """Compute a 0..100 risk score based on entities and context.
    Simple weighted sum + context multiplier, clamped to 100.
    """
    base = 0
    for e in entities or []:
        label = (e.get('label') or '').upper()
        base += ENTITY_WEIGHTS.get(label, 7)
    mult = CONTEXT_MULTIPLIER.get((context or 'general').lower(), 1.0)
    score = min(100, int(round(base * mult)))
    return score
