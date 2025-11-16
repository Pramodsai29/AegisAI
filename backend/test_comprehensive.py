#!/usr/bin/env python3
"""
Comprehensive test script for sanitizer - tests all PII types with various formats.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.sanitizer import sanitize_text

def test_comprehensive():
    """Comprehensive test with real-world examples."""
    
    test_cases = [
        {
            "name": "Names - Simple",
            "input": "My name is John Doe.",
            "should_contain": ["[[PERSON_"],
            "should_not_contain": ["John Doe"]
        },
        {
            "name": "Names - Multiple",
            "input": "Contact John Smith or Mary Jane Watson for details.",
            "should_contain": ["[[PERSON_"],
            "should_not_contain": ["John Smith", "Mary Jane Watson"]
        },
        {
            "name": "PAN - Single",
            "input": "My PAN is ABCDE1234F.",
            "should_contain": ["[[PAN_"],
            "should_not_contain": ["ABCDE1234F"]
        },
        {
            "name": "PAN - Multiple",
            "input": "PAN: ABCDE1234F and XYZAB5678C.",
            "should_contain": ["[[PAN_"],
            "should_not_contain": ["ABCDE1234F", "XYZAB5678C"]
        },
        {
            "name": "Aadhaar - With Spaces",
            "input": "Aadhaar: 1234 5678 9012",
            "should_contain": ["[[AADHAAR_"],
            "should_not_contain": ["1234 5678 9012"]
        },
        {
            "name": "Aadhaar - With Hyphens",
            "input": "Aadhaar: 9876-5432-1098",
            "should_contain": ["[[AADHAAR_"],
            "should_not_contain": ["9876-5432-1098"]
        },
        {
            "name": "Card - With Spaces",
            "input": "Card: 1234 5678 9012 3456",
            "should_contain": ["[[CARD_"],
            "should_not_contain": ["1234 5678 9012 3456"]
        },
        {
            "name": "Card - With Hyphens",
            "input": "Card: 4532-1234-5678-9010",
            "should_contain": ["[[CARD_"],
            "should_not_contain": ["4532-1234-5678-9010"]
        },
        {
            "name": "Account - Continuous",
            "input": "Account: 1234567890123456",
            "should_contain": ["[[ACC_"],
            "should_not_contain": ["1234567890123456"]
        },
        {
            "name": "Email - Single",
            "input": "Email: john.doe@example.com",
            "should_contain": ["[[EMAIL_"],
            "should_not_contain": ["john.doe@example.com"]
        },
        {
            "name": "Phone - International",
            "input": "Phone: +91 98765 43210",
            "should_contain": ["[[PHONE_"],
            "should_not_contain": ["+91 98765 43210"]
        },
        {
            "name": "Phone - US Format",
            "input": "Phone: 123-456-7890",
            "should_contain": ["[[PHONE_"],
            "should_not_contain": ["123-456-7890"]
        },
        {
            "name": "Currency - Multiple",
            "input": "Paid Rs. 5000, $100, and EUR 250",
            "should_contain": ["[[CURRENCY_"],
            "should_not_contain": ["Rs. 5000", "$100"]
        },
        {
            "name": "Real World - Financial",
            "input": "Hi, I'm Rajesh Kumar. My PAN is ABCDE1234F, account is 1234567890123456, and I paid Rs. 50000.",
            "should_contain": ["[[PERSON_", "[[PAN_", "[[ACC_", "[[CURRENCY_"],
            "should_not_contain": ["Rajesh Kumar", "ABCDE1234F", "1234567890123456", "Rs. 50000"]
        },
        {
            "name": "Real World - Personal Info",
            "input": "Contact John Doe at john.doe@email.com or call +1 555-123-4567. His SSN is 123-45-6789.",
            "should_contain": ["[[PERSON_", "[[EMAIL_", "[[PHONE_", "[[SSN_"],
            "should_not_contain": ["John Doe", "john.doe@email.com", "+1 555-123-4567", "123-45-6789"]
        },
        {
            "name": "Edge Case - Card vs Aadhaar",
            "input": "Card: 1234 5678 9012 3456 and Aadhaar: 1234 5678 9012",
            "should_contain": ["[[CARD_", "[[AADHAAR_"],
            "should_not_contain": ["1234 5678 9012 3456", "1234 5678 9012"]
        },
        {
            "name": "Edge Case - Account vs Card",
            "input": "Account: 1234567890123456 (no spaces) and Card: 4532 1234 5678 9010 (with spaces)",
            "should_contain": ["[[ACC_", "[[CARD_"],
            "should_not_contain": ["1234567890123456", "4532 1234 5678 9010"]
        }
    ]
    
    print("=" * 80)
    print("COMPREHENSIVE SANITIZER TEST")
    print("=" * 80)
    print()
    
    passed = 0
    failed = 0
    
    for i, test in enumerate(test_cases, 1):
        print(f"Test {i}: {test['name']}")
        print(f"Input: {test['input']}")
        
        try:
            sanitized, entities, context, confidence, rehydration_map = sanitize_text(test['input'])
            
            print(f"Sanitized: {sanitized}")
            print(f"Entities: {len(entities)} found")
            for entity in entities:
                print(f"  - {entity['entity'][:30]}... -> {entity['label']}")
            
            # Check rehydration
            rehydrated = sanitized
            for placeholder, original in rehydration_map.items():
                rehydrated = rehydrated.replace(placeholder, original)
            
            # Validation
            test_passed = True
            issues = []
            
            # Check should_contain
            for pattern in test['should_contain']:
                if pattern not in sanitized:
                    test_passed = False
                    issues.append(f"Missing expected pattern: {pattern}")
            
            # Check should_not_contain
            for pattern in test['should_not_contain']:
                if pattern in sanitized:
                    test_passed = False
                    issues.append(f"Found unmasked PII: {pattern}")
            
            # Verify rehydration works
            for original in test['should_not_contain']:
                if original not in rehydrated:
                    test_passed = False
                    issues.append(f"Rehydration failed for: {original}")
            
            if test_passed:
                print("[PASS]")
                passed += 1
            else:
                print("[FAIL]")
                for issue in issues:
                    print(f"  - {issue}")
                failed += 1
                
        except Exception as e:
            print(f"[ERROR] {str(e)}")
            import traceback
            traceback.print_exc()
            failed += 1
        
        print()
        print("-" * 80)
        print()
    
    print("=" * 80)
    print(f"RESULTS: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    print("=" * 80)
    
    return failed == 0

if __name__ == "__main__":
    success = test_comprehensive()
    sys.exit(0 if success else 1)

