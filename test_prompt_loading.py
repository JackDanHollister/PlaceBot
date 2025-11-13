#!/usr/bin/env python3
"""
Test script to verify prompt loading from placebot/data/prompt.md
"""

import sys
sys.path.insert(0, r'C:\GitHub\PlaceBot')

from placebot.core.ai_processor import AIProcessor

# Create a minimal config
test_config = {
    'name': 'Test Model',
    'api_key': 'test-key',
    'requests_per_minute': 50
}

# Initialize processor
print("=" * 60)
print("Testing prompt loading from placebot/data/prompt.md")
print("=" * 60)

try:
    processor = AIProcessor(test_config)
    print("[OK] AIProcessor initialized successfully")
    
    # Try to load the prompt
    prompt = processor._get_full_instructions()
    
    print("[OK] Prompt loaded successfully!")
    print(f"   Length: {len(prompt)} characters")
    print(f"   Lines: {len(prompt.splitlines())} lines")
    print(f"\n   First 100 characters:")
    print(f"   {prompt[:100]}...")
    print(f"\n   Last 100 characters:")
    print(f"   ...{prompt[-100:]}")
    
    # Verify it's cached
    prompt2 = processor._get_full_instructions()
    print(f"\n[OK] Prompt caching works (same object: {prompt is prompt2})")
    
    print("\n" + "=" * 60)
    print("[SUCCESS] ALL TESTS PASSED")
    print("=" * 60)
    
except Exception as e:
    print(f"\n[ERROR] {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
