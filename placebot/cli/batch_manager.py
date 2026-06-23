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
from placebot.core.data_dirs import get_batch_jobs_dir, get_input_dir, get_output_dir
from placebot.core.field_mapping import get_identifier, safe_custom_id
from placebot.core.file_manager import DatasetManager
from placebot.core.output_formatter import OutputFormatter


def _load_source_records(dataset_filename):
    """Load the original dataset (if still present) indexed by barcode/ID,
    so downloaded batch results can be merged back with the source columns."""
    index = {}
    if not dataset_filename:
        return index
    try:
        dm = DatasetManager(input_folder=str(get_input_dir()),
                            output_folder=str(get_output_dir()))
        for ds in dm.discover_datasets():
            if ds['filename'] == dataset_filename:
                for rec in dm.load_dataset(ds):
                    # Resolve the identifier from native or Darwin Core columns
                    # (occurrenceID, catalogNumber, ...), not just a hard-coded
                    # "Barcode" column, so DwC/GBIF files merge correctly.
                    bc = get_identifier(rec, default="")
                    if bc:
                        index[str(bc)] = rec
                        # Also index under the batch custom_id so results whose
                        # identifier was shortened (>64 chars) map back here.
                        index.setdefault(safe_custom_id(bc), rec)
                break
    except Exception as e:
        print(f"   ⚠️  Could not load source dataset for merge: {e}")
    return index


def _load_source_record_list(dataset_filename):
    """Load the original dataset as an ordered list (if still present), so
    deduplicated batch results can be re-expanded onto every original record."""
    if not dataset_filename:
        return []
    try:
        dm = DatasetManager(input_folder=str(get_input_dir()),
                            output_folder=str(get_output_dir()))
        for ds in dm.discover_datasets():
            if ds['filename'] == dataset_filename:
                return dm.load_dataset(ds)
    except Exception as e:
        print(f"   ⚠️  Could not load source dataset for re-expansion: {e}")
    return []


def _results_to_records(results, source_index):
    """Map raw batch results into the standard output schema, merging the
    original dataset columns where available. Every result yields one record."""
    records = []
    for r in results:
        barcode = str(r.get('barcode', ''))
        rec = dict(source_index.get(barcode, {}))
        # When the custom_id was shortened, recover the real identifier from the
        # merged source columns; otherwise fall back to the custom_id itself.
        rec.setdefault('Barcode', get_identifier(rec, default=barcode))
        if r.get('success'):
            rec.update({
                'Country_Processed': r.get('country', ''),
                'State': r.get('state', ''),
                'Region': r.get('region', ''),
                'Sector': r.get('sector', ''),
                'Exact_Site': r.get('exact_site', ''),
                'Latitude': r.get('latitude'),
                'Longitude': r.get('longitude'),
                'Coordinate_Source': r.get('coordinate_source', ''),
                'Coordinate_Radius_Meters': r.get('coordinate_radius_meters'),
                'Elevation': r.get('elevation_meters'),
                'Confidence': r.get('confidence', 'medium'),
                'Processing_Notes': r.get('notes', ''),
            })
        else:
            rec['Confidence'] = 'low'
            rec['Processing_Notes'] = f"Batch processing failed: {r.get('error', 'unknown')}"
        records.append(rec)
    return records


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


def load_batch_info(batch_dir=None):
    """Load all batch job info files."""
    if batch_dir is None:
        batch_dir = str(get_batch_jobs_dir())
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


def check_job_status(batch_id, batch_dir=None):
    """Check status of a specific job."""
    if batch_dir is None:
        batch_dir = str(get_batch_jobs_dir())
    
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


def download_job(batch_id, batch_dir=None):
    """Download results from a completed job."""
    if batch_dir is None:
        batch_dir = str(get_batch_jobs_dir())
    
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

        # Map results into the standard schema, merging original dataset columns
        source_index = _load_source_records(job_info.get('dataset'))
        records = _results_to_records(results, source_index)

        # If the job was deduplicated at submission, re-expand the results onto
        # every original record by reloading the source file (joined on the
        # deterministic locality+country key). Falls back to the deduplicated
        # output if the original file is no longer available.
        if job_info.get('deduplicated'):
            from placebot.core.deduplication import reconstitute_records
            original_records = _load_source_record_list(job_info.get('dataset'))
            if original_records:
                records, expand_stats = reconstitute_records(original_records, records)
                print(
                    f"♻️  Re-expanded onto {expand_stats['total']} original records "
                    f"({expand_stats['matched']} matched a georeference)"
                )
            else:
                print("   ⚠️  Original input file not found; leaving results deduplicated.")

        # Honour the output formats chosen at submission time (default to CSV)
        formats = job_info.get('output_formats') or ['csv']
        # Honour the Darwin Core output choice made at submission time
        use_dwc = bool(job_info.get('use_dwc', False))

        output_dir = get_output_dir()
        output_dir.mkdir(parents=True, exist_ok=True)
        base_path = str(output_dir / f"{job_info['batch_name']}_results")

        written = OutputFormatter.write_output(records, base_path, formats, dwc=use_dwc)

        success_count = sum(1 for r in results if r.get('success'))
        total = len(results)
        print(f"✅ Downloaded {total} results ({success_count}/{total} successful)")
        if success_count < total:
            print(f"   ⚠️  {total - success_count} record(s) failed - see Processing_Notes")
        for fmt, path in written.items():
            print(f"💾 {fmt.upper()}: {path}")
        return True

    except Exception as e:
        print(f"❌ Error downloading: {e}")
        import traceback
        traceback.print_exc()
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
