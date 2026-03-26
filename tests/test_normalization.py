import json
import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.sentinel.normalizer import Normalizer

def test_normalization():
    normalizer = Normalizer()
    corpus_path = os.path.join("tests", "normalization_corpus.jsonl")
    
    passed = 0
    failed = 0
    
    print(f"--- Running Canonicalization Test Suite ---")
    
    with open(corpus_path, "r") as f:
        for i, line in enumerate(f):
            test_case = json.loads(line)
            input_str = test_case["input"]
            expected = test_case["expected"]
            category = test_case["category"]
            
            actual = normalizer.normalize(input_str)
            
            if actual == expected:
                print(f"✅ [{category}] PASS: {input_str!r} -> {actual!r}")
                passed += 1
            else:
                print(f"❌ [{category}] FAIL: {input_str!r}")
                print(f"    Expected: {expected!r}")
                print(f"    Actual:   {actual!r}")
                failed += 1
                
    print(f"\n--- Result: {passed} passed, {failed} failed ---")
    return failed == 0

if __name__ == "__main__":
    if test_normalization():
        sys.exit(0)
    else:
        sys.exit(1)
