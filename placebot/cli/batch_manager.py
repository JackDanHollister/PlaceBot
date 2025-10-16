#!/usr/bin/env python3
"""
Batch Job Manager
=================

Manage batch processing jobs: list, check status, download results.

Usage:
    placebot-batch list           # List all batch jobs
    placebot-batch status <id>    # Check status of a job
    placebot-batch download <id>  # Download results
    placebot-batch download-last  # Download most recent completed job
    placebot-batch check-all      # Check status of all pending jobs
"""

import sys
import json
import os
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv
load_dotenv()

from placebot.core.async_batch_processor import (
    AnthropicBatchProcessor,
    OpenAIBatchProcessor,
)
from placebot.core.async_batch_processor import GeminiBatchProcessor


def get_batch_processor(provider, api_key, model_id):
    """Get the appropriate batch processor."""
    provider = provider.lower()
    
    if 'anthropic' in provider:
        return AnthropicBatchProcessor(api_key, model_id)
    elif 'openai' in provider:
        return OpenAIBatchProcessor(api_key, model_id)
    elif 'google' in provider or 'gemini' in provider:
        return GeminiBatchProcessor(api_key, model_id)
    else:
        return None


def load_batch_info(batch_dir='./output/batch_jobs'):
    """Load all batch job info files."""
    if not os.path.exists(batch_dir):
        return []
    
    jobs = []
    for filename in os.listdir(batch_dir):
        if filename.endswith('_info.json'):
            try:
                with open(os.path.join(batch_dir, filename)) as f:
                    job_info = json.load(f)
                    job_info['info_file'] = filename
                    jobs.append(job_info)
            except (json.JSONDecodeError, IOError) as e:
                print(f"⚠️  Skipping corrupted file: {filename}")
                continue
    
    # Sort by submission time (newest first)
    jobs.sort(key=lambda x: x.get('submitted_at', ''), reverse=True)
    return jobs


def list_jobs():
    """List all batch jobs."""
    jobs = load_batch_info()
    
    if not jobs:
        print("📋 No batch jobs found")
        return
    
    print(f"\n📋 BATCH JOBS ({len(jobs)} total)")
    print("="*80)
    
    for i, job in enumerate(jobs, 1):
        print(f"\n{i}. {job['batch_name']}")
        print(f"   ID: {job['batch_id']}")
        print(f"   Provider: {job['provider']}")
        print(f"   Model: {job['model']}")
        print(f"   Dataset: {job['dataset']}")
        print(f"   Records: {job['record_count']}")
        print(f"   Submitted: {job['submitted_at']}")


def check_job_status(batch_id, batch_dir='./output/batch_jobs'):
    """Check status of a specific job."""
    # Find job info
    job_info = None
    for filename in os.listdir(batch_dir):
        if filename.endswith('_info.json'):
            try:
                with open(os.path.join(batch_dir, filename)) as f:
                    info = json.load(f)
                    if info['batch_id'] == batch_id:
                        job_info = info
                        break
            except (json.JSONDecodeError, IOError):
                continue
    
    if not job_info:
        print(f"❌ Job not found: {batch_id}")
        return None
    
    # Get API key
    from placebot.core.config import get_config
    config = get_config()
    provider = job_info['provider']
    
    if 'anthropic' in provider:
        api_key = config.get_api_key('anthropic')
    elif 'openai' in provider:
        api_key = config.get_api_key('openai')
    else:
        api_key = config.get_api_key('google')
    
    processor = get_batch_processor(provider, api_key, job_info['model'])
    if not processor:
        print(f"❌ Unknown provider: {provider}")
        return None
    
    status = processor.check_status(batch_id)
    
    print(f"\n📊 BATCH STATUS")
    print("="*80)
    print(f"Batch ID: {batch_id}")
    print(f"Name: {job_info['batch_name']}")
    print(f"Status: {status.get('status')}")
    
    if status.get('total', 0) > 0:
        print(f"Progress: {status.get('succeeded', 0)}/{status.get('total', 0)} succeeded")
    
    return status


def download_job(batch_id, batch_dir='./output/batch_jobs'):
    """Download results from a completed job."""
    # Similar to check_job_status but calls get_results
    # Find job info
    job_info = None
    for filename in os.listdir(batch_dir):
        if filename.endswith('_info.json'):
            try:
                with open(os.path.join(batch_dir, filename)) as f:
                    info = json.load(f)
                    if info['batch_id'] == batch_id:
                        job_info = info
                        break
            except (json.JSONDecodeError, IOError):
                continue
    
    if not job_info:
        print(f"❌ Job not found: {batch_id}")
        return False
    
    # Get API key
    from placebot.core.config import get_config
    config = get_config()
    provider = job_info['provider']
    
    if 'anthropic' in provider:
        api_key = config.get_api_key('anthropic')
    elif 'openai' in provider:
        api_key = config.get_api_key('openai')
    else:
        api_key = config.get_api_key('google')
    
    processor = get_batch_processor(provider, api_key, job_info['model'])
    if not processor:
        print(f"❌ Unknown provider: {provider}")
        return False
    
    print(f"\n📥 Downloading results...")
    try:
        results = processor.get_results(batch_id)
        
        # Save results
        output_file = f"./output/{job_info['batch_name']}_results.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        success_count = sum(1 for r in results if r.get('success'))
        print(f"✅ Downloaded {len(results)} results ({success_count} successful)")
        print(f"💾 Saved to: {output_file}")
        return True
        
    except Exception as e:
        print(f"❌ Error downloading: {e}")
        return False


def download_last():
    """Download the most recent completed job."""
    jobs = load_batch_info()
    
    if not jobs:
        print("📋 No batch jobs found")
        return
    
    # Check recent jobs for completed ones
    for job in jobs[:10]:  # Check last 10
        status = check_job_status(job['batch_id'])
        if status and ('ended' in status.get('status', '').lower() or 
                      'succeeded' in status.get('status', '').lower() or
                      'completed' in status.get('status', '').lower()):
            print(f"\n✅ Found completed job: {job['batch_name']}")
            return download_job(job['batch_id'])
    
    print("⏳ No completed jobs found yet")


def check_all():
    """Check status of all jobs."""
    jobs = load_batch_info()
    
    if not jobs:
        print("📋 No batch jobs found")
        return
    
    print(f"\n🔍 Checking {len(jobs)} batch jobs...")
    print("="*80)
    
    for job in jobs:
        print(f"\n📊 {job['batch_name']}")
        status = check_job_status(job['batch_id'])


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    
    command = sys.argv[1]
    
    if command == 'list':
        list_jobs()
    elif command == 'status' and len(sys.argv) > 2:
        check_job_status(sys.argv[2])
    elif command == 'download' and len(sys.argv) > 2:
        download_job(sys.argv[2])
    elif command == 'download-last':
        download_last()
    elif command == 'check-all':
        check_all()
    else:
        print(__doc__)
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
