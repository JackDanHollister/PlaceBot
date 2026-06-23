#!/usr/bin/env python3
"""
Staggered Batch Results Downloader
===================================

Download and merge results from all sub-batches in a staggered batch job.

Usage:
    python -m placebot.cli.batch_download_staggered <staggered_summary_file>

Example:
    python -m placebot.cli.batch_download_staggered ./output/batch_jobs/BGE_1_Gemini_2.5_Pro_20251013_203958_staggered_summary.json
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
load_dotenv(root_path / ".env")
load_dotenv(root_path / "config" / ".env")

from placebot.core.data_dirs import get_output_dir

from placebot.core.async_batch_processor import (
    AnthropicBatchProcessor,
    OpenAIBatchProcessor,
    GeminiBatchProcessor,
)


def build_processor_for_summary(summary):
    """Create the right batch processor for a staggered summary's provider."""
    provider = summary["provider"].lower()
    if "anthropic" in provider:
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        return AnthropicBatchProcessor(api_key, summary["model"])
    elif "openai" in provider:
        api_key = os.getenv("OPENAI_API_KEY", "")
        return OpenAIBatchProcessor(api_key, summary["model"])
    elif "google" in provider or "gemini" in provider:
        api_key = os.getenv("GOOGLE_API_KEY", "") or os.getenv("GEMINI_API_KEY", "")
        return GeminiBatchProcessor(api_key, summary["model"])
    return None


def fetch_staggered_results(summary_file):
    """Download and merge every sub-batch without printing (for the GUI).

    Returns a dict::

        {'success': bool, 'records': [...], 'merged_file': str|None,
         'summary': {...}, 'expected': int, 'failed': [...], 'error': str|None}
    """
    if not os.path.exists(summary_file):
        return {"success": False, "error": f"Summary file not found: {summary_file}"}

    with open(summary_file, encoding="utf-8") as f:
        summary = json.load(f)

    processor = build_processor_for_summary(summary)
    if processor is None:
        return {
            "success": False,
            "error": f"Unknown provider: {summary['provider']}",
            "summary": summary,
        }

    all_results = []
    failed = []
    for batch_info in summary.get("batches", []):
        try:
            results = processor.get_results(batch_info["batch_id"])
            if results:
                all_results.extend(results)
            else:
                failed.append(batch_info)
        except Exception as e:
            failed.append({**batch_info, "error": str(e)})

    # Map the raw AI output into the canonical schema and merge the original
    # dataset columns, mirroring the single-batch and CLI download paths.
    from placebot.cli.batch_manager import _load_source_records, _results_to_records

    source_index = _load_source_records(summary.get("dataset"))
    records = _results_to_records(all_results, source_index) if all_results else []

    merged_file = None
    if records:
        output_dir = str(get_output_dir())
        os.makedirs(output_dir, exist_ok=True)
        base = os.path.basename(summary_file).replace("_staggered_summary.json", "")
        merged_file = os.path.join(output_dir, f"{base}_merged_results.json")
        with open(merged_file, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2, ensure_ascii=False)

    return {
        "success": bool(all_results),
        "records": records,
        "merged_file": merged_file,
        "summary": summary,
        "expected": summary.get("total_records", 0),
        "failed": failed,
        "error": (
            None
            if all_results
            else "No results available yet (sub-batches may still be processing)."
        ),
    }


def download_staggered_batch_results(summary_file):
    """Download results from all sub-batches in a staggered batch job."""

    # Load summary
    if not os.path.exists(summary_file):
        print(f"[ERROR] Summary file not found: {summary_file}")
        return

    with open(summary_file) as f:
        summary = json.load(f)

    print(f"\n[INFO] DOWNLOADING STAGGERED BATCH RESULTS")
    print("=" * 80)
    print(f"Dataset: {summary['dataset']}")
    print(f"Total records: {summary['total_records']}")
    print(f"Total batches: {summary['batches_submitted']}")
    print(f"Provider: {summary['provider']}")
    print()

    # Get API credentials
    provider = summary["provider"].lower()

    # Initialize appropriate batch processor
    if "anthropic" in provider:
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        processor = AnthropicBatchProcessor(api_key, summary["model"])
    elif "openai" in provider:
        api_key = os.getenv("OPENAI_API_KEY", "")
        processor = OpenAIBatchProcessor(api_key, summary["model"])
    elif "google" in provider or "gemini" in provider:
        api_key = os.getenv("GOOGLE_API_KEY", "") or os.getenv("GEMINI_API_KEY", "")
        processor = GeminiBatchProcessor(api_key, summary["model"])
    else:
        print(f"[ERROR] Unknown provider: {provider}")
        return

    # Download results from each batch
    all_results = []
    failed_batches = []

    for batch_info in summary["batches"]:
        batch_num = batch_info["batch_number"]
        batch_id = batch_info["batch_id"]
        record_count = batch_info["record_count"]

        print(f"[INFO] Batch {batch_num}/{summary['batches_submitted']}: {batch_id}")
        print(f"   Records: {record_count}")

        try:
            # Download results
            results = processor.get_results(batch_id)

            if results:
                print(f"   [SUCCESS] Downloaded {len(results)} results")
                all_results.extend(results)
            else:
                print(f"   [WARNING] No results yet")
                failed_batches.append(batch_info)

        except Exception as e:
            print(f"   [ERROR] Error: {e}")
            failed_batches.append(batch_info)

        print()

    # Summary
    print("=" * 80)
    print(f"[INFO] DOWNLOAD SUMMARY:")
    print(f"   Total results downloaded: {len(all_results)}")
    print(f"   Expected results: {summary['total_records']}")
    print(
        f"   Success rate: {len(all_results)}/{summary['total_records']} ({len(all_results)/summary['total_records']*100:.1f}%)"
    )

    if failed_batches:
        print(f"\n[WARNING] Failed batches: {len(failed_batches)}")
        for batch_info in failed_batches:
            print(f"   - Batch {batch_info['batch_number']}: {batch_info['batch_id']}")

    # Save merged results
    if all_results:
        output_dir = str(get_output_dir())
        os.makedirs(output_dir, exist_ok=True)

        # Extract base name from summary file
        summary_base = os.path.basename(summary_file).replace(
            "_staggered_summary.json", ""
        )
        results_file = os.path.join(output_dir, f"{summary_base}_merged_results.json")

        with open(results_file, "w", encoding="utf-8") as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False)

        print(f"\n[INFO] Merged results saved to: {results_file}")
        print(f"[SUCCESS] Download complete!")

        # Also save to CSV if requested
        output_formats = summary.get("output_formats", [])
        if "csv" in output_formats:
            csv_file = results_file.replace(".json", ".csv")
            try:
                import pandas as pd

                df = pd.DataFrame(all_results)
                df.to_csv(csv_file, index=False)
                print(f"[INFO] CSV saved to: {csv_file}")
            except Exception as e:
                print(f"[WARNING] Could not save CSV: {e}")
    else:
        print(f"\n[ERROR] No results downloaded")

    return len(all_results)


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python -m placebot.cli.batch_download_staggered <summary_file>")
        print()
        print("Example:")
        print("  python -m placebot.cli.batch_download_staggered \\")
        print("    ./output/batch_jobs/BGE_1_..._staggered_summary.json")
        sys.exit(1)

    summary_file = sys.argv[1]
    download_staggered_batch_results(summary_file)


if __name__ == "__main__":
    main()
