#!/usr/bin/env python3
"""
Batch Results Downloader
=========================

Download and process results from completed batch jobs.

Usage:
    python -m placebot.cli.batch_download <batch_id>
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


def download_batch_results(batch_id, batch_dir='./output/batch_jobs'):
    """Download results from a completed batch job."""
    
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
    
    print(f"\nDOWNLOADING BATCH RESULTS")
    print("=" * 80)
    print(f"Batch ID: {batch_id}")
    print(f"Name: {info['batch_name']}")
    print(f"Records: {info['record_count']}")
    print()
    
    # Get API credentials
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
    
    # Download results
    try:
        print("[INFO] Downloading results from API...")
        results = processor.get_results(batch_id)
        
        if not results:
            print("[ERROR] No results found")
            return
        
        print(f"[SUCCESS] Downloaded {len(results)} results")
        
        # Save results to file
        output_dir = './output'
        os.makedirs(output_dir, exist_ok=True)
        
        results_file = os.path.join(output_dir, f"{info['batch_name']}_results.json")
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"[INFO] Results saved to: {results_file}")
        print(f"\n[SUCCESS] Download complete!")
        
    except Exception as e:
        print(f"[ERROR] Error downloading results: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python -m placebot.cli.batch_download <batch_id>")
        sys.exit(1)
    
    batch_id = sys.argv[1]
    download_batch_results(batch_id)


if __name__ == '__main__':
    main()
