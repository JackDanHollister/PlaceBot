#!/usr/bin/env python3
"""
Batch Status Checker
====================

Check the status of async batch processing jobs.

Usage:
    python -m placebot.cli.batch_status <batch_id>
    python -m placebot.cli.batch_status --list
"""

import sys
import json
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Load environment variables from .env file
from dotenv import load_dotenv
# Load from both possible locations
root_path = Path(__file__).parent.parent.parent
load_dotenv(root_path / '.env')
load_dotenv(root_path / 'config' / '.env')

from placebot.core.async_batch_processor import (
    AnthropicBatchProcessor,
    OpenAIBatchProcessor,
    GeminiBatchProcessor
)


def list_batch_jobs(batch_dir='./output/batch_jobs'):
    """List all batch jobs with their info."""
    if not os.path.exists(batch_dir):
        print("[ERROR] No batch jobs found")
        return
    
    info_files = [f for f in os.listdir(batch_dir) if f.endswith('_info.json')]
    
    if not info_files:
        print("[ERROR] No batch jobs found")
        return
    
    print(f"\nBATCH JOBS ({len(info_files)} total)")
    print("=" * 80)
    
    for info_file in sorted(info_files):
        with open(os.path.join(batch_dir, info_file)) as f:
            info = json.load(f)
        
        print(f"\n[BATCH] {info['batch_name']}")
        print(f"   ID: {info['batch_id']}")
        print(f"   Provider: {info['provider']}")
        print(f"   Records: {info['record_count']}")
        print(f"   Submitted: {info['submitted_at']}")


def check_batch_status(batch_id, batch_dir='./output/batch_jobs'):
    """Check status of a specific batch job."""
    
    # Find the batch info file
    info_file = None
    if os.path.exists(batch_dir):
        for f in os.listdir(batch_dir):
            if f.endswith('_info.json'):
                path = os.path.join(batch_dir, f)
                try:
                    # Skip empty files
                    if os.path.getsize(path) == 0:
                        continue
                    with open(path) as file:
                        info = json.load(file)
                        if info['batch_id'] == batch_id:
                            info_file = path
                            break
                except (json.JSONDecodeError, KeyError):
                    continue
    
    if not info_file:
        print(f"[ERROR] Batch {batch_id} not found")
        return
    
    # Load batch info
    with open(info_file) as f:
        info = json.load(f)
    
    print(f"\nBATCH STATUS")
    print("=" * 80)
    print(f"Batch ID: {batch_id}")
    print(f"Name: {info['batch_name']}")
    print(f"Provider: {info['provider']}")
    print(f"Model: {info['model']}")
    print(f"Records: {info['record_count']}")
    print(f"Submitted: {info['submitted_at']}")
    print()
    
    # Get API credentials from environment
    provider = info['provider'].lower()
    
    # Initialize appropriate batch processor
    if 'anthropic' in provider:
        api_key = os.getenv('ANTHROPIC_API_KEY', '')
        processor = AnthropicBatchProcessor(api_key, info['model'])
    elif 'openai' in provider:
        api_key = os.getenv('OPENAI_API_KEY', '')
        processor = OpenAIBatchProcessor(api_key, info['model'])
    elif 'google' in provider or 'gemini' in provider:
        from placebot.core.async_batch_processor import GeminiBatchProcessor
        api_key = os.getenv('GOOGLE_API_KEY', '') or os.getenv('GEMINI_API_KEY', '')
        processor = GeminiBatchProcessor(api_key, info['model'])
    else:
        print(f"[ERROR] Unknown provider: {provider}")
        return
    
    # Check status
    try:
        status = processor.check_status(batch_id)
        
        print(f"Status: {status.get('status', 'unknown')}")
        
        if 'total' in status:
            # OpenAI uses 'completed', Claude uses 'succeeded'
            succeeded = status.get('succeeded', 0) or status.get('completed', 0)
            total = status.get('total', 0)
            failed = status.get('failed', 0)
            processing = status.get('processing', 0)
            
            print(f"Progress: {succeeded}/{total} succeeded")
            if processing > 0:
                print(f"Processing: {processing}")
            if failed > 0:
                print(f"Failed: {failed}")
            
            # Check if completed
            is_complete = (succeeded == total and total > 0) or status.get('status') in ['completed', 'ended']
            
            if is_complete:
                print("\n[SUCCESS] Batch processing complete!")
                if failed > 0:
                    print(f"[WARNING] {failed} requests failed")
                print(f"\n[INFO] To download results:")
                print(f"   python -m placebot.cli.batch_download {batch_id}")
            else:
                print(f"\n[INFO] Still processing... Check again later")
        else:
            print(f"Details: {status}")
            
    except Exception as e:
        print(f"[ERROR] Error checking status: {e}")


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python -m placebot.cli.batch_status <batch_id>")
        print("       python -m placebot.cli.batch_status --list")
        sys.exit(1)
    
    if sys.argv[1] == '--list':
        list_batch_jobs()
    else:
        batch_id = sys.argv[1]
        check_batch_status(batch_id)


if __name__ == '__main__':
    main()
