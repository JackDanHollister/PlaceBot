#!/usr/bin/env python3
"""
Staggered Batch Status Checker
================================

Check status of all sub-batches in a staggered batch job.

Usage:
    python -m placebot.cli.batch_status_staggered <staggered_summary_file>
    
Example:
    python -m placebot.cli.batch_status_staggered ./output/batch_jobs/BGE_1_Gemini_2.5_Pro_20251013_203958_staggered_summary.json
"""

import sys
import json
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Load environment variables
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


def check_staggered_batch_status(summary_file):
    """Check status of all sub-batches in a staggered batch job."""
    
    # Load summary
    if not os.path.exists(summary_file):
        print(f"[ERROR] Summary file not found: {summary_file}")
        return
    
    with open(summary_file) as f:
        summary = json.load(f)
    
    print(f"\n[INFO] STAGGERED BATCH STATUS")
    print("=" * 80)
    print(f"Dataset: {summary['dataset']}")
    print(f"Total records: {summary['total_records']}")
    print(f"Total batches: {summary['batches_submitted']}")
    print(f"Provider: {summary['provider']}")
    print(f"Model: {summary['model']}")
    print(f"Submitted: {summary['submitted_at']}")
    print()
    
    # Get API credentials
    provider = summary['provider'].lower()
    
    # Initialize appropriate batch processor
    if 'anthropic' in provider:
        api_key = os.getenv('ANTHROPIC_API_KEY', '')
        processor = AnthropicBatchProcessor(api_key, summary['model'])
    elif 'openai' in provider:
        api_key = os.getenv('OPENAI_API_KEY', '')
        processor = OpenAIBatchProcessor(api_key, summary['model'])
    elif 'google' in provider or 'gemini' in provider:
        api_key = os.getenv('GOOGLE_API_KEY', '') or os.getenv('GEMINI_API_KEY', '')
        processor = GeminiBatchProcessor(api_key, summary['model'])
    else:
        print(f"[ERROR] Unknown provider: {provider}")
        return
    
    # Check status of each batch
    completed = 0
    failed = 0
    pending = 0
    total_succeeded = 0
    total_failed = 0
    
    print("[INFO] BATCH STATUS:")
    print("-" * 80)
    
    for batch_info in summary['batches']:
        batch_num = batch_info['batch_number']
        batch_id = batch_info['batch_id']
        record_count = batch_info['record_count']
        
        print(f"\nBatch {batch_num}/{summary['batches_submitted']}: {batch_id}")
        print(f"  Records: {record_count} (rows {batch_info['start_record']}-{batch_info['end_record']})")
        
        try:
            # Check status
            status = processor.check_status(batch_id)
            
            status_display = status.get('status', 'unknown')
            print(f"  Status: {status_display}")
            
            if status_display in ['completed', 'succeeded', 'success']:
                completed += 1
                succeeded = status.get('succeeded', 0)
                failed_count = status.get('failed', 0)
                total_succeeded += succeeded
                total_failed += failed_count
                print(f"  [SUCCESS] Complete: {succeeded} succeeded, {failed_count} failed")
            elif status_display in ['failed', 'error']:
                failed += 1
                print(f"  [ERROR] Failed")
            else:
                pending += 1
                progress = status.get('succeeded', 0)
                if progress > 0:
                    print(f"  [INFO] In progress: {progress}/{record_count}")
                else:
                    print(f"  [INFO] Pending...")
        
        except Exception as e:
            print(f"  [ERROR] Error checking status: {e}")
            failed += 1
    
    # Overall summary
    print()
    print("=" * 80)
    print(f"[INFO] OVERALL STATUS:")
    print(f"  Completed batches: {completed}/{summary['batches_submitted']}")
    print(f"  Pending batches: {pending}/{summary['batches_submitted']}")
    print(f"  Failed batches: {failed}/{summary['batches_submitted']}")
    
    if completed > 0:
        print(f"\n  Total results: {total_succeeded} succeeded, {total_failed} failed")
        print(f"  Progress: {total_succeeded + total_failed}/{summary['total_records']} records processed")
    
    if completed == summary['batches_submitted']:
        print(f"\n[SUCCESS] All batches complete!")
        print(f"\n[INFO] Download results:")
        print(f"   python -m placebot.cli.batch_download_staggered {summary_file}")
    elif pending > 0:
        print(f"\n[INFO] {pending} batch(es) still processing...")
        print(f"   Check again in a few minutes")
    
    if failed > 0:
        print(f"\n[WARNING] {failed} batch(es) failed - check individual batches for errors")


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python -m placebot.cli.batch_status_staggered <summary_file>")
        print()
        print("Example:")
        print("  python -m placebot.cli.batch_status_staggered \\")
        print("    ./output/batch_jobs/BGE_1_..._staggered_summary.json")
        sys.exit(1)
    
    summary_file = sys.argv[1]
    check_staggered_batch_status(summary_file)


if __name__ == '__main__':
    main()
