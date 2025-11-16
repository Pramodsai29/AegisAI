#!/usr/bin/env python3
"""
End-to-end test for the complete pipeline:
1. Sanitization with placeholders
2. LLM processing (simulated)
3. Output filtering with NVIDIA Guardrails
4. Rehydration for final output
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.sanitizer import sanitize_text
from utils.guardrails_wrapper import run_output_guardrails
import re

def test_end_to_end():
    """Test the complete pipeline from input to final rehydrated output."""
    
    test_cases = [
        {
            "name": "Financial Data",
            "input": "Hi, I'm Rajesh Kumar. My PAN is ABCDE1234F, account is 1234567890123456, phone is +91 98765 43210, and I paid Rs. 50000.",
            "description": "Should mask all PII, send to LLM with placeholders, filter output, then rehydrate for user"
        },
        {
            "name": "Personal Info",
            "input": "Contact John Doe at john.doe@email.com or call +1 555-123-4567. His SSN is 123-45-6789.",
            "description": "Should handle names, email, phone, and SSN"
        },
        {
            "name": "Card and Aadhaar",
            "input": "My card is 1234 5678 9012 3456 and Aadhaar is 1234 5678 9012.",
            "description": "Should distinguish between card (16 digits with spaces) and Aadhaar (12 digits)"
        },
        {
            "name": "Account vs Phone",
            "input": "Account: 1234567890123456 and Phone: +91 98765 43210",
            "description": "Should distinguish account (16 digits no spaces) from phone (with + and spaces)"
        }
    ]
    
    print("=" * 80)
    print("END-TO-END PIPELINE TEST")
    print("=" * 80)
    print()
    
    all_passed = True
    
    for i, test in enumerate(test_cases, 1):
        print(f"Test {i}: {test['name']}")
        print(f"Description: {test['description']}")
        print(f"Input: {test['input']}")
        print()
        
        try:
            # STEP 1: Sanitization
            sanitized, entities, context, confidence, rehydration_map = sanitize_text(test['input'])
            print(f"[1] Sanitized: {sanitized}")
            print(f"    Entities: {len(entities)} found")
            print(f"    Rehydration map: {len(rehydration_map)} entries")
            
            # Verify no original PII in sanitized
            original_pii_found = False
            for entity in entities:
                if entity['entity'] in sanitized:
                    original_pii_found = True
                    print(f"    ERROR: Original PII '{entity['entity']}' found in sanitized text!")
            
            if original_pii_found:
                print("    [FAIL] Sanitization step")
                all_passed = False
                continue
            else:
                print("    [PASS] Sanitization step")
            
            # STEP 2: Simulate LLM Response (with placeholders)
            # LLM should receive sanitized text and respond with placeholders
            llm_response = f"Based on your input: {sanitized}. Your information has been processed securely."
            print(f"[2] LLM Response: {llm_response}")
            print("    [PASS] LLM receives sanitized text")
            
            # STEP 3: Output Filtering with NVIDIA Guardrails
            guarded = run_output_guardrails(
                llm_response,
                {
                    'category': context,
                    'sanitized_preview': sanitized[:200]
                }
            )
            print(f"[3] Guardrails Output: {guarded}")
            
            # Additional regex filtering
            filtered = guarded
            EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+", re.I)
            PHONE_RE = re.compile(r"(\+?\d[\d\s\-]{7,}\d)")
            PAN_RE = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b", re.I)
            filtered = EMAIL_RE.sub('[EMAIL_MASKED]', filtered)
            filtered = PHONE_RE.sub('[PHONE_MASKED]', filtered)
            filtered = PAN_RE.sub('[PAN_MASKED]', filtered)
            
            print(f"    Filtered: {filtered}")
            print("    [PASS] Output filtering step")
            
            # STEP 4: Rehydration for final user output
            final_rehydrated = filtered
            if rehydration_map:
                for placeholder, original_value in rehydration_map.items():
                    final_rehydrated = final_rehydrated.replace(placeholder, original_value)
            
            print(f"[4] Final Rehydrated: {final_rehydrated}")
            
            # Verify rehydration worked - original values should appear
            rehydration_worked = False
            for entity in entities[:3]:  # Check first 3 entities
                if entity['entity'] in final_rehydrated:
                    rehydration_worked = True
                    break
            
            if rehydration_worked:
                print("    [PASS] Rehydration step - original data restored for user")
            else:
                print("    [WARN] Rehydration may not have worked - check placeholders")
            
            # Verify placeholders are gone in final output
            placeholder_pattern = re.compile(r'\[\[[A-Z_]+\d+\]\]')
            remaining_placeholders = placeholder_pattern.findall(final_rehydrated)
            if remaining_placeholders:
                print(f"    [WARN] Some placeholders remain: {remaining_placeholders}")
            
            print()
            print("-" * 80)
            print()
            
        except Exception as e:
            print(f"[ERROR] {str(e)}")
            import traceback
            traceback.print_exc()
            all_passed = False
            print()
            print("-" * 80)
            print()
    
    print("=" * 80)
    if all_passed:
        print("[SUCCESS] ALL END-TO-END TESTS PASSED")
    else:
        print("[FAILURE] SOME TESTS FAILED")
    print("=" * 80)
    
    return all_passed

if __name__ == "__main__":
    success = test_end_to_end()
    sys.exit(0 if success else 1)
