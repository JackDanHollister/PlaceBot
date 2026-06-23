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
from placebot.core.data_dirs import get_output_dir, get_batch_jobs_dir


def find_batch_info(batch_id, batch_dir=None):
    """Locate and load the ``*_info.json`` file for a given batch id.

    Returns the parsed info dict, or ``None`` if no matching job is found.
    """
    if batch_dir is None:
        batch_dir = str(get_batch_jobs_dir())

    if os.path.exists(batch_dir):
        for f in os.listdir(batch_dir):
            if f.endswith('_info.json'):
                path = os.path.join(batch_dir, f)
                try:
                    if os.path.getsize(path) == 0:
                        continue
                    with open(path) as file:
                        info = json.load(file)
                        if info.get('batch_id') == batch_id:
                            return info
                except (json.JSONDecodeError, KeyError):
                    continue
    return None


def build_processor_for_info(info):
    """Create the right batch processor for a job's provider.

    Returns the processor instance, or ``None`` for an unknown provider.
    """
    provider = info['provider'].lower()
    if 'anthropic' in provider:
        api_key = os.getenv('ANTHROPIC_API_KEY', '')
        return AnthropicBatchProcessor(api_key, info['model'])
    elif 'openai' in provider:
        api_key = os.getenv('OPENAI_API_KEY', '')
        return OpenAIBatchProcessor(api_key, info['model'])
    elif 'google' in provider or 'gemini' in provider:
        api_key = os.getenv('GOOGLE_API_KEY', '') or os.getenv('GEMINI_API_KEY', '')
        return GeminiBatchProcessor(api_key, info['model'])
    return None


def fetch_batch_results(batch_id, batch_dir=None):
    """Download and persist results for a batch job without any printing.

    Designed for programmatic callers such as the GUI. Returns a dict::

        {'success': bool, 'records': [...], 'results_file': str,
         'info': {...}, 'error': str|None}
    """
    info = find_batch_info(batch_id, batch_dir)
    if not info:
        return {'success': False, 'error': f"Batch {batch_id} not found"}

    processor = build_processor_for_info(info)
    if processor is None:
        return {'success': False, 'error': f"Unknown provider: {info['provider']}", 'info': info}

    try:
        results = processor.get_results(batch_id)
    except Exception as e:
        return {'success': False, 'error': str(e), 'info': info}

    if not results:
        return {'success': False, 'error': 'No results available yet (batch may still be processing).', 'info': info}

    # Map the raw AI output into the canonical output schema and merge the
    # original dataset columns, mirroring the CLI download path. Without this
    # the saved file keeps lowercase AI keys and the GUI's reconstitution (which
    # copies capitalised georeference columns) finds nothing to add.
    from placebot.cli.batch_manager import _load_source_records, _results_to_records

    source_index = _load_source_records(info.get('dataset'))
    records = _results_to_records(results, source_index)

    output_dir = str(get_output_dir())
    os.makedirs(output_dir, exist_ok=True)
    results_file = os.path.join(output_dir, f"{info['batch_name']}_results.json")
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(records, f, indent=2, ensure_ascii=False)

    return {
        'success': True,
        'records': records,
        'results_file': results_file,
        'info': info,
        'error': None,
    }


def download_batch_results(batch_id, batch_dir=None):
    """Download results from a completed batch job (CLI entry point)."""
    info = find_batch_info(batch_id, batch_dir)
    if not info:
        print(f"[ERROR] Batch {batch_id} not found")
        return

    print(f"\nDOWNLOADING BATCH RESULTS")
    print("=" * 80)
    print(f"Batch ID: {batch_id}")
    print(f"Name: {info['batch_name']}")
    print(f"Records: {info['record_count']}")
    print()

    print("[INFO] Downloading results from API...")
    result = fetch_batch_results(batch_id, batch_dir)

    if not result['success']:
        print(f"[ERROR] {result['error']}")
        return

    print(f"[SUCCESS] Downloaded {len(result['records'])} results")
    print(f"[INFO] Results saved to: {result['results_file']}")
    print(f"\n[SUCCESS] Download complete!")


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python -m placebot.cli.batch_download <batch_id>")
        sys.exit(1)
    
    batch_id = sys.argv[1]
    download_batch_results(batch_id)


if __name__ == '__main__':
    main()
