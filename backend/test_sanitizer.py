#!/usr/bin/env python3
"""
Test script for sanitizer with reversible placeholder masking.
Tests all PII types and verifies rehydration works correctly.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.sanitizer import sanitize_text

def test_sanitizer():
    """Test comprehensive PII masking and rehydration."""
    
    test_cases = [
        {
            "name": "Names Test",
            "input": "My name is John Doe and I work with Mary Jane Smith.",
            "expected_masked": ["PERSON"],
            "description": "Should mask all names"
        },
        {
            "name": "PAN Test",
            "input": "My PAN number is ABCDE1234F and my friend's is XYZAB5678C.",
            "expected_masked": ["PAN"],
            "description": "Should mask PAN numbers"
        },
        {
            "name": "Aadhaar Test",
            "input": "My Aadhaar is 1234 5678 9012 and my wife's is 9876-5432-1098.",
            "expected_masked": ["AADHAAR"],
            "description": "Should mask Aadhaar numbers"
        },
        {
            "name": "Email Test",
            "input": "Contact me at john.doe@example.com or jane@test.org.",
            "expected_masked": ["EMAIL"],
            "description": "Should mask email addresses"
        },
        {
            "name": "Phone Test",
            "input": "Call me at +91 98765 43210 or 123-456-7890.",
            "expected_masked": ["PHONE"],
            "description": "Should mask phone numbers"
        },
        {
            "name": "Card Test",
            "input": "My card is 1234 5678 9012 3456 and CVV is 123.",
            "expected_masked": ["CARD"],
            "description": "Should mask credit card numbers"
        },
        {
            "name": "Account Test",
            "input": "My account number is 1234567890123456.",
            "expected_masked": ["ACC"],
            "description": "Should mask account numbers"
        },
        {
            "name": "Currency Test",
            "input": "I paid Rs. 5000, $100, and Rs. 2500 for the items.",
            "expected_masked": ["CURRENCY"],
            "description": "Should mask currency amounts"
        },
        {
            "name": "IP Address Test",
            "input": "The server IP is 192.168.1.1 and backup is 10.0.0.1.",
            "expected_masked": ["IP"],
            "description": "Should mask IP addresses"
        },
        {
            "name": "URL Test",
            "input": "Visit https://example.com or http://test.org for more info.",
            "expected_masked": ["URL"],
            "description": "Should mask URLs"
        },
        {
            "name": "SSN Test",
            "input": "My SSN is 123-45-6789.",
            "expected_masked": ["SSN"],
            "description": "Should mask SSN"
        },
        {
            "name": "Comprehensive Test",
            "input": "Hi, I'm John Doe. My PAN is ABCDE1234F, Aadhaar is 1234 5678 9012, email is john@example.com, phone is +91 98765 43210, and I paid Rs. 5000.",
            "expected_masked": ["PERSON", "PAN", "AADHAAR", "EMAIL", "PHONE", "CURRENCY"],
            "description": "Should mask all PII types in one text"
        }
    ]
    
    print("=" * 80)
    print("SANITIZER TEST SUITE")
    print("=" * 80)
    print()
    
    all_passed = True
    
    for i, test in enumerate(test_cases, 1):
        print(f"Test {i}: {test['name']}")
        print(f"Description: {test['description']}")
        print(f"Input: {test['input']}")
        print()
        
        try:
            sanitized, entities, context, confidence, rehydration_map = sanitize_text(test['input'])
            
            print(f"Sanitized: {sanitized}")
            print(f"Entities found: {len(entities)}")
            for entity in entities:
                print(f"  - {entity['entity']} -> {entity['label']}")
            print(f"Rehydration map entries: {len(rehydration_map)}")
            print()
            
            # Check if expected types were masked
            found_labels = {e['label'] for e in entities}
            expected_labels = set(test['expected_masked'])
            
            # Verify masking occurred
            has_placeholders = any(f"[[{label}_" in sanitized for label in expected_labels)
            
            # Verify rehydration works
            rehydrated = sanitized
            for placeholder, original in rehydration_map.items():
                rehydrated = rehydrated.replace(placeholder, original)
            
            print(f"Rehydrated text: {rehydrated}")
            print()
            
            # Test results
            test_passed = True
            issues = []
            
            # Check if placeholders were created
            if not has_placeholders and expected_labels:
                test_passed = False
                issues.append(f"Expected placeholders for {expected_labels} but found: {found_labels}")
            
            # Check if rehydration restores original (for non-overlapping cases)
            # Note: Some entities might overlap, so we check if original values appear in rehydrated
            original_values = [e['entity'] for e in entities]
            rehydrated_has_originals = any(val in rehydrated for val in original_values)
            
            if not rehydrated_has_originals and entities:
                test_passed = False
                issues.append("Rehydration did not restore original values")
            
            # Check if sanitized text doesn't contain original PII
            sanitized_has_pii = any(val in sanitized for val in original_values if len(val) > 3)
            if sanitized_has_pii:
                test_passed = False
                issues.append("Sanitized text still contains original PII values")
            
            if test_passed:
                print("[PASS] Test passed")
            else:
                print("[FAIL] Test failed")
                for issue in issues:
                    print(f"  - {issue}")
                all_passed = False
        
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
        print("[SUCCESS] ALL TESTS PASSED")
    else:
        print("[FAILURE] SOME TESTS FAILED")
    print("=" * 80)
    
    return all_passed

if __name__ == "__main__":
    success = test_sanitizer()
    sys.exit(0 if success else 1)

