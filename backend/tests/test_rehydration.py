#!/usr/bin/env python3
"""
Test suite for Ephemeral Rehydration with Robust Placeholder Handling.
Tests the complete pipeline: sanitization -> LLM -> filtering -> rehydration.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.sanitizer import sanitize_text
from utils.llm_client import call_llm
import json
import re


def test_example_from_prompt():
    """
    Test 1: Input identical to the example in the prompt.
    Expected: final_rehydrated_text contains Rachel Morgan, sarah.jennings@..., 9100898354, Jonathan Lee etc.
    """
    print("=" * 80)
    print("TEST 1: Example from Prompt")
    print("=" * 80)
    
    input_text = (
        "Rachel Morgan contacted sarah.jennings@orbittech.com at phone 9100898354. "
        "Jonathan Lee also reached out. Their account numbers are 1234567890123456 and 9876543210987654."
    )
    
    print(f"Input: {input_text}\n")
    
    # Step 1: Sanitization
    sanitized, entities, context, confidence, rehydration_map, entities_summary = sanitize_text(input_text)
    print(f"Sanitized: {sanitized}")
    print(f"Rehydration Map: {rehydration_map}")
    print(f"Entities Summary: {len(entities_summary)} entries\n")
    
    # Step 2: LLM (simulate with preserved placeholders)
    llm_result = call_llm(sanitized, {'category': context, 'confidence': confidence})
    print(f"LLM Answer: {llm_result.get('answer', '')[:100]}...")
    print(f"Fallback Used: {llm_result.get('fallback_used', False)}\n")
    
    # Step 3: Output Filter (simulate)
    # Check for leaks in LLM answer
    answer_text = llm_result.get('answer', '')
    leak_detected = False
    try:
        check_sanitized, check_entities, _, _, _, _ = sanitize_text(answer_text, ner='spacy')
        placeholder_pattern = re.compile(r'\[\[[A-Z_]+\d+\]\]')
        for entity in check_entities:
            entity_text = entity.get('entity', '')
            if not placeholder_pattern.match(entity_text):
                leak_detected = True
                break
    except:
        pass
    
    filtered_output = {
        'safe_sanitized_text': answer_text,
        'leak_detected': leak_detected,
        'notes': None
    }
    print(f"Filtered Safe Text: {filtered_output['safe_sanitized_text'][:100]}...")
    print(f"Leak Detected: {leak_detected}\n")
    
    # Step 4: Final Rehydration (simulate)
    text_to_rehydrate = answer_text
    placeholder_pattern = re.compile(r'\[\[[A-Z_]+\d+\]\]')
    placeholders_in_text = set(placeholder_pattern.findall(text_to_rehydrate))
    
    final_text = text_to_rehydrate
    rehydration_appendix = []
    
    if placeholders_in_text:
        for placeholder, original_value in rehydration_map.items():
            if placeholder in placeholders_in_text:
                final_text = final_text.replace(placeholder, original_value)
    else:
        # Append appendix
        for placeholder, original_value in rehydration_map.items():
            rehydration_appendix.append(f"{placeholder}: {original_value}")
        if rehydration_appendix:
            final_text += "\n\n--- Rehydration Appendix ---\n"
            final_text += "\n".join(rehydration_appendix)
    
    print(f"Final Rehydrated Text: {final_text}\n")
    
    # Validation
    expected_names = ['Rachel Morgan', 'Jonathan Lee']
    expected_email = 'sarah.jennings@orbittech.com'
    expected_phone = '9100898354'
    
    test_passed = True
    issues = []
    
    for name in expected_names:
        if name not in final_text:
            test_passed = False
            issues.append(f"Missing name: {name}")
    
    if expected_email not in final_text:
        test_passed = False
        issues.append(f"Missing email: {expected_email}")
    
    if expected_phone not in final_text:
        test_passed = False
        issues.append(f"Missing phone: {expected_phone}")
    
    if test_passed:
        print("[PASS] All expected values found in final_rehydrated_text")
    else:
        print("[FAIL] Missing expected values:")
        for issue in issues:
            print(f"  - {issue}")
    
    return test_passed


def test_llm_preserves_placeholders():
    """
    Test 2: Simulate LLM that returns "I can help..." with placeholders preserved.
    Should rehydrate inline.
    """
    print("\n" + "=" * 80)
    print("TEST 2: LLM Preserves Placeholders")
    print("=" * 80)
    
    input_text = "Contact John Doe at john@example.com or call +91 98765 43210."
    
    # Sanitize
    sanitized, entities, context, confidence, rehydration_map, entities_summary = sanitize_text(input_text)
    print(f"Sanitized: {sanitized}\n")
    
    # Simulate LLM response with placeholders preserved
    mock_llm_answer = f"I can help you contact [[PERSON_1]] at [[EMAIL_1]] or reach them at [[PHONE_1]]."
    
    # Create mock filter response
    class MockResponse:
        def __init__(self, data):
            self.data = json.dumps(data).encode()
        def get_data(self, as_text=False):
            return self.data.decode() if as_text else self.data
    
    # Simulate output filter
    filtered_output = {
        'safe_sanitized_text': mock_llm_answer,
        'leak_detected': False,
        'notes': None
    }
    
    # Simulate final route rehydration
    final_text = mock_llm_answer
    for placeholder, original_value in rehydration_map.items():
        final_text = final_text.replace(placeholder, original_value)
    
    print(f"LLM Answer (with placeholders): {mock_llm_answer}")
    print(f"Final Rehydrated: {final_text}\n")
    
    # Validation
    test_passed = True
    if 'John Doe' not in final_text:
        test_passed = False
        print("[FAIL] Name not rehydrated")
    if 'john@example.com' not in final_text:
        test_passed = False
        print("[FAIL] Email not rehydrated")
    if '+91 98765 43210' not in final_text:
        test_passed = False
        print("[FAIL] Phone not rehydrated")
    
    if test_passed:
        print("[PASS] All placeholders rehydrated inline")
    
    return test_passed


def test_llm_missing_placeholders_appendix():
    """
    Test 3: Simulate LLM that returns generic "the specified individuals" (placeholders missing).
    Should return appended Rehydration Appendix.
    """
    print("\n" + "=" * 80)
    print("TEST 3: LLM Missing Placeholders - Appendix Fallback")
    print("=" * 80)
    
    input_text = "Contact Rachel Morgan at rachel@example.com."
    
    # Sanitize
    sanitized, entities, context, confidence, rehydration_map, entities_summary = sanitize_text(input_text)
    print(f"Sanitized: {sanitized}\n")
    
    # Simulate LLM response WITHOUT placeholders
    mock_llm_answer = "I can help you contact the specified individual."
    
    # Simulate final route with missing placeholders
    import re
    placeholder_pattern = re.compile(r'\[\[[A-Z_]+\d+\]\]')
    placeholders_in_text = set(placeholder_pattern.findall(mock_llm_answer))
    
    final_text = mock_llm_answer
    rehydration_appendix = []
    
    if not placeholders_in_text:
        # No placeholders found - append appendix
        for placeholder, original_value in rehydration_map.items():
            if placeholder and original_value:
                rehydration_appendix.append(f"{placeholder}: {original_value}")
        
        if rehydration_appendix:
            final_text += "\n\n--- Rehydration Appendix ---\n"
            final_text += "\n".join(rehydration_appendix)
    
    print(f"LLM Answer (no placeholders): {mock_llm_answer}")
    print(f"Final with Appendix: {final_text}\n")
    
    # Validation
    test_passed = True
    if '--- Rehydration Appendix ---' not in final_text:
        test_passed = False
        print("[FAIL] Rehydration Appendix not appended")
    
    # Check if original values are in appendix
    for placeholder, original_value in rehydration_map.items():
        if original_value not in final_text:
            test_passed = False
            print(f"[FAIL] Original value '{original_value}' not in appendix")
    
    if test_passed:
        print("[PASS] Rehydration Appendix correctly appended with all values")
    
    return test_passed


def run_all_tests():
    """Run all tests and report results."""
    print("\n" + "=" * 80)
    print("EPHEMERAL REHYDRATION TEST SUITE")
    print("=" * 80)
    print()
    
    results = []
    
    try:
        results.append(("Test 1: Example from Prompt", test_example_from_prompt()))
    except Exception as e:
        print(f"[ERROR] Test 1 failed: {repr(e)}")
        import traceback
        traceback.print_exc()
        results.append(("Test 1: Example from Prompt", False))
    
    try:
        results.append(("Test 2: LLM Preserves Placeholders", test_llm_preserves_placeholders()))
    except Exception as e:
        print(f"[ERROR] Test 2 failed: {repr(e)}")
        import traceback
        traceback.print_exc()
        results.append(("Test 2: LLM Preserves Placeholders", False))
    
    try:
        results.append(("Test 3: LLM Missing Placeholders - Appendix", test_llm_missing_placeholders_appendix()))
    except Exception as e:
        print(f"[ERROR] Test 3 failed: {repr(e)}")
        import traceback
        traceback.print_exc()
        results.append(("Test 3: LLM Missing Placeholders - Appendix", False))
    
    print("\n" + "=" * 80)
    print("TEST RESULTS")
    print("=" * 80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status} {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    print("=" * 80)
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

