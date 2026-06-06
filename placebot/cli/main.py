#!/usr/bin/env python3
"""
Locality Processor - Main CLI Entry Point
==========================================

Command-line interface for the locality processor.
Supports real-time and batch processing modes.
"""

import argparse
import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from placebot.core.batch_processor import BatchProcessor
from placebot.core.async_batch_processor import AnthropicBatchProcessor, OpenAIBatchProcessor, GeminiBatchProcessor
from placebot.core.file_manager import DatasetManager, OutputManager
from placebot.core.model_selector import discover_models, load_model_profile, select_model_interactive
from placebot.core.model_comparison import ModelComparison
from placebot.core.dataset_preview import DatasetPreview
from placebot.core.cost_estimator import CostEstimator
from placebot.core.output_formatter import OutputFormatter
from placebot.core.config import get_config
from placebot.core.data_dirs import setup_directories, get_input_dir, get_output_dir, show_directory_info
from placebot.cli.user_interface import UserInterface


def setup_api_keys():
    """Check and setup API keys from .env file or environment variables."""
    config = get_config()
    keys_status = config.check_api_keys()
    
    missing_keys = [k for k, v in keys_status.items() if not v]
    
    if missing_keys:
        print("⚠️  Warning: Some API keys are not set:")
        for key in missing_keys:
            print(f"   - {key.upper()}_API_KEY")
        print("\n💡 Set them in your environment or .env file")
        print("   Local models (Ollama) don't require API keys\n")
    
    return len(missing_keys) == 0


def run_interactive_mode(args):
    """Run the interactive processing mode (original workflow)."""
    # Setup data directories (auto-creates if needed)
    setup_directories()
    
    # Use user's data directories if not overridden
    input_dir = args.input_dir if args.input_dir != './input' else str(get_input_dir())
    output_dir = args.output_dir if args.output_dir != './output' else str(get_output_dir())
    
    # Initialize managers
    dataset_manager = DatasetManager(
        input_folder=input_dir,
        output_folder=output_dir
    )
    output_manager = OutputManager  # Static class, no initialization needed
    
    # Show welcome
    UserInterface.show_welcome()
    
    # Check API keys
    setup_api_keys()
    
    # Discover datasets
    datasets = dataset_manager.discover_datasets()
    
    if not datasets:
        print("❌ No datasets found.")
        print()
        show_directory_info()
        return 1
    
    # Select dataset (this will display datasets internally)
    selected_dataset = UserInterface.select_dataset(datasets)
    if selected_dataset is None:
        print("❌ Invalid dataset selection")
        return 1
    
    # Ask for processing mode
    processing_mode = UserInterface.prompt_processing_mode()
    
    # Show dataset preview
    dataset_data = dataset_manager.load_dataset(selected_dataset)
    DatasetPreview.display_preview(dataset_data, num_samples=3)
    
    # Discover and select model
    available_models = discover_models()
    if not available_models:
        print("❌ No model profiles found in models/ directory")
        return 1
    
    # Load all model configs for comparison
    model_configs = []
    for model_name in available_models:
        config = load_model_profile(model_name)
        if config:
            model_configs.append(config)
    
    # Show model comparison
    if model_configs:
        comparisons = ModelComparison.compare_models(
            model_configs,
            num_records=selected_dataset['row_count'],
            processing_mode=processing_mode
        )
        ModelComparison.display_comparison(comparisons, sort_by='cost')
    
    # Select model interactively (returns full model config)
    model_config = select_model_interactive()
    if not model_config:
        print("❌ No model selected")
        return 1
    
    # Show cost estimate
    model_name = model_config.get('name', 'Unknown')
    cost_est = CostEstimator.estimate_cost(
        selected_dataset['row_count'],
        model_config,
        processing_mode=processing_mode,
        with_caching='cached' in model_name.lower()
    )
    
    print(f"\n💰 COST ESTIMATE")
    print(f"Records: {cost_est['num_records']:,}")
    print(f"Mode: {processing_mode}")
    print(f"Estimated Cost: ${cost_est['estimated_cost']:.4f}")
    print(f"Total Savings: ${cost_est['total_savings']:.4f} ({cost_est['savings_percentage']:.0f}%)")
    print()
    
    # Ask for output formats
    output_formats = UserInterface.prompt_output_formats()
    print(f"✅ Output formats: {', '.join(output_formats)}")
    
    # Process based on mode
    print(f"\n🚀 Starting processing...")
    
    if processing_mode == 'batch' or processing_mode == 'staggered':
        # Use async batch API (50% cost savings)
        if processing_mode == 'staggered':
            print(f"📦 Using staggered batch API (50% cheaper, quota-safe)")
        else:
            print(f"📦 Using async batch API (50% cheaper, results in 24 hours)")
        
        # Determine which batch processor to use based on provider
        provider = model_config.get('provider', '').lower()
        api_key = model_config.get('api_key', '')
        model_id = model_config.get('model_id', '')
        
        if 'anthropic' in provider:
            batch_processor = AnthropicBatchProcessor(api_key, model_id)
        elif 'openai' in provider:
            batch_processor = OpenAIBatchProcessor(api_key, model_id)
        elif 'google' in provider or 'gemini' in provider:
            from placebot.core.async_batch_processor import GeminiBatchProcessor
            batch_processor = GeminiBatchProcessor(api_key, model_id)
        else:
            print(f"⚠️  Batch mode not supported for {provider}, using real-time mode")
            processing_mode = 'realtime'
            batch_processor = None
        
        if processing_mode == 'batch' or processing_mode == 'staggered':
            # Load dataset
            records = dataset_manager.load_dataset(selected_dataset)
            
            if processing_mode == 'staggered':
                print(f"📊 Loading {len(records)} records for staggered batch processing...")
            else:
                print(f"📊 Preparing {len(records)} records for batch processing...")
            
            # Get instructions from AI processor
            from placebot.core.ai_processor import AIProcessor
            ai_proc = AIProcessor(model_config)
            base_instructions = ai_proc._get_full_instructions()
            
            # Create prompt template for batch processing
            # Just pass the base instructions - locality and country will be appended per record
            prompt_template = base_instructions
            
            # Create output directory for batch files
            import os
            batch_dir = os.path.join(output_dir, 'batch_jobs')
            os.makedirs(batch_dir, exist_ok=True)
            
            # Prepare batch file based on provider
            from datetime import datetime
            import os
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            # Extract filename without extension
            filename_stem = os.path.splitext(selected_dataset['filename'])[0]
            # Replace spaces in model name to avoid issues with command-line arguments
            model_name_safe = model_config.get('name', 'model').replace(' ', '_')
            batch_name = f"{filename_stem}_{model_name_safe}_{timestamp}"
            
            # Check if staggered mode - handle differently
            if processing_mode == 'staggered':
                # STAGGERED BATCH MODE - split into multiple smaller batches
                import json
                
                print(f"\n📊 STAGGERED BATCH CONFIGURATION")
                print("=" * 70)
                
                # Calculate optimal batch size based on provider
                total_records = len(records)
                if 'google' in provider or 'gemini' in provider:
                    batch_size = 500  # Smaller batches to avoid quota issues
                    delay_seconds = 120  # Longer delay between batches
                    print(f"   Provider: Gemini (optimized for quota limits)")
                elif 'anthropic' in provider:
                    batch_size = 1000
                    delay_seconds = 30
                    print(f"   Provider: Anthropic")
                else:  # OpenAI
                    batch_size = 2000
                    delay_seconds = 10
                    print(f"   Provider: OpenAI")
                
                num_batches = (total_records + batch_size - 1) // batch_size
                actual_batch_size = min(batch_size, total_records)
                
                print(f"   Total records: {total_records}")
                if num_batches > 1:
                    print(f"   Batch size: {batch_size} records (max)")
                    print(f"   Number of batches: {num_batches}")
                    print(f"   Delay between batches: {delay_seconds}s")
                else:
                    print(f"   Batch size: {actual_batch_size} records (all in one batch)")
                    print(f"   Number of batches: 1 (no splitting needed)")
                print()
                
                response = input("Continue with staggered submission? (y/n): ").strip().lower()
                if response != 'y':
                    print("❌ Cancelled")
                    return 1
                
                print()
                
                # Submit batches with delays
                import time
                batch_info_list = []
                
                for batch_num in range(num_batches):
                    start_idx = batch_num * batch_size
                    end_idx = min((batch_num + 1) * batch_size, total_records)
                    
                    print(f"📤 Batch {batch_num + 1}/{num_batches}")
                    print(f"   Records: {start_idx + 1} to {end_idx} ({end_idx - start_idx} records)")
                    
                    # Get records for this batch
                    batch_records = records[start_idx:end_idx]
                    
                    # Create batch name
                    sub_batch_name = f"{batch_name}_batch{batch_num + 1}of{num_batches}"
                    
                    try:
                        # Prepare and submit based on provider
                        if 'anthropic' in provider:
                            requests_list = batch_processor.prepare_batch_requests(batch_records, prompt_template)
                            sub_batch_id = batch_processor.submit_batch(requests_list, sub_batch_name)
                        elif 'google' in provider or 'gemini' in provider:
                            requests_list = batch_processor.prepare_batch_requests(batch_records, prompt_template)
                            sub_batch_id = batch_processor.submit_batch(requests_list, sub_batch_name)
                        else:  # OpenAI
                            batch_file = os.path.join(batch_dir, f"{sub_batch_name}.jsonl")
                            batch_processor.prepare_batch_file(batch_records, prompt_template, batch_file)
                            sub_batch_id = batch_processor.submit_batch(batch_file, sub_batch_name)
                        
                        # Save individual batch info
                        sub_batch_info = {
                            'batch_number': batch_num + 1,
                            'total_batches': num_batches,
                            'batch_id': sub_batch_id,
                            'batch_name': sub_batch_name,
                            'provider': provider,
                            'model': model_id,
                            'dataset': selected_dataset['filename'],
                            'start_record': start_idx + 1,
                            'end_record': end_idx,
                            'record_count': end_idx - start_idx,
                            'submitted_at': timestamp,
                            'output_formats': output_formats
                        }
                        batch_info_list.append(sub_batch_info)
                        
                        # Save individual batch info file
                        sub_info_file = os.path.join(batch_dir, f"{sub_batch_name}_info.json")
                        with open(sub_info_file, 'w', encoding='utf-8') as f:
                            json.dump(sub_batch_info, f, indent=2, ensure_ascii=False)
                        
                        print(f"   ✅ Submitted: {sub_batch_id}")
                        print()
                        
                        # Wait before next batch (except for last one)
                        if batch_num < num_batches - 1:
                            print(f"   ⏳ Waiting {delay_seconds}s before next batch...")
                            time.sleep(delay_seconds)
                            print()
                    
                    except Exception as e:
                        print(f"   ❌ Error: {e}")
                        print(f"   ⚠️  Stopping after {batch_num} batches")
                        break
                
                # Save master summary
                summary_file = os.path.join(batch_dir, f"{batch_name}_staggered_summary.json")
                with open(summary_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        'total_records': total_records,
                        'batch_size': batch_size,
                        'batches_submitted': len(batch_info_list),
                        'provider': provider,
                        'model': model_id,
                        'dataset': selected_dataset['filename'],
                        'submitted_at': timestamp,
                        'output_formats': output_formats,
                        'batches': batch_info_list
                    }, f, indent=2, ensure_ascii=False)
                
                print(f"\n🎉 Staggered batch submission complete!")
                print(f"   📊 Batches submitted: {len(batch_info_list)}/{num_batches}")
                print(f"   📝 Total records: {sum(b['record_count'] for b in batch_info_list)}/{total_records}")
                print(f"   💾 Summary saved: {summary_file}")
                print(f"\n🔍 Check status of all batches:")
                print(f"   python -m placebot.cli.batch_status_staggered {summary_file}")
                print(f"\n📥 Download and merge results when complete:")
                print(f"   python -m placebot.cli.batch_download_staggered {summary_file}")
                print(f"\n💡 Each batch will complete independently within 24 hours")
                
                return 0
            
            else:
                # REGULAR BATCH MODE - submit as single batch
                if 'anthropic' in provider:
                    print("📝 Preparing Anthropic batch requests...")
                    requests_list = batch_processor.prepare_batch_requests(records, prompt_template)
                    print("📤 Submitting to Anthropic Batch API...")
                    batch_id = batch_processor.submit_batch(requests_list, batch_name)
                
                elif 'google' in provider or 'gemini' in provider:
                    print("📝 Preparing Gemini batch requests...")
                    requests_list = batch_processor.prepare_batch_requests(records, prompt_template)
                    print("📤 Submitting to Gemini Batch API...")
                    batch_id = batch_processor.submit_batch(requests_list, batch_name)
                    
                else:  # OpenAI
                    batch_file = os.path.join(batch_dir, f"{batch_name}.jsonl")
                    print(f"📝 Creating batch file: {batch_file}")
                    batch_processor.prepare_batch_file(records, prompt_template, batch_file)
                    print("📤 Submitting batch job...")
                    batch_id = batch_processor.submit_batch(batch_file, batch_name)
            
            # Regular single batch mode - save info
            batch_info_file = os.path.join(batch_dir, f"{batch_name}_info.json")
            import json
            with open(batch_info_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'batch_id': batch_id,
                    'batch_name': batch_name,
                    'provider': provider,
                    'model': model_id,
                    'dataset': selected_dataset['filename'],
                    'record_count': len(records),
                    'submitted_at': timestamp,
                    'output_formats': output_formats
                }, f, indent=2, ensure_ascii=False)
            
            print(f"\n✅ Batch submitted successfully!")
            print(f"   📋 Batch ID: {batch_id}")
            print(f"   💾 Info saved: {batch_info_file}")
            print(f"\n⏳ Processing will complete within 24 hours (usually much faster)")
            print(f"\n📊 To check status later:")
            print(f"   python -m placebot.cli.batch_status {batch_id}")
            print(f"\n💡 Results will be downloaded automatically when ready")
            
            return 0
    
    if processing_mode == 'realtime':
        # Use real-time synchronous processing
        print(f"⚡ Using real-time processing")
        
        # Get batch size only for real-time mode (affects API call grouping, not cost)
        batch_size = UserInterface.get_batch_size()
        
        # Initialize batch processor
        processor = BatchProcessor(dataset_manager, output_manager)
        
        # Process dataset
        results = processor.process_dataset(
            selected_dataset,
            model_config,
            batch_size=batch_size,
            save_progress=True
        )
        
        print(f"\n✅ Real-time processing completed!")
        print(f"   Results saved to output directory")
    
    return 0


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description='Locality Processor - Extract coordinates from locality descriptions',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode (default)
  placebot

  # Launch the graphical interface
  placebot-gui

  # Specify custom directories
  placebot --input-dir ./data --output-dir ./results

For more information, visit: https://github.com/JackDanHollister/PlaceBot
"""
    )
    
    parser.add_argument(
        '--input-dir',
        type=str,
        default='./input',
        help='Input directory containing CSV/TSV files (default: ~/.placebot/input)'
    )
    
    parser.add_argument(
        '--output-dir',
        type=str,
        default='./output',
        help='Output directory for results (default: ~/.placebot/output)'
    )
    
    parser.add_argument(
        '--show-dirs',
        action='store_true',
        help='Show PlaceBot data directories and exit'
    )
    
    parser.add_argument(
        '--batch',
        action='store_true',
        help='Use batch processing mode (50%% cost savings, results in 24h)'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='placebot 1.1.1'
    )
    
    args = parser.parse_args()
    
    # Handle --show-dirs flag
    if args.show_dirs:
        show_directory_info()
        return 0
    
    # Check if batch mode is requested
    if args.batch:
        print("💡 Batch processing is available — just choose 'Batch' (or "
              "'Staggered') when prompted for a processing mode.\n")
    
    # Run interactive mode
    try:
        return run_interactive_mode(args)
    except KeyboardInterrupt:
        print("\n\n⚠️  Processing interrupted by user")
        return 130
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
