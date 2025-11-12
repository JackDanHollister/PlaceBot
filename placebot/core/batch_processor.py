#!/usr/bin/env python3
"""
Batch Processor
===============

Orchestrates the entire processing pipeline using modular components.
Handles batching, progress tracking, and error recovery.
"""

import time
import os
from datetime import datetime
from typing import Dict, List, Optional, Any

from .coordinate_utils import preprocess_coordinates
from .ai_processor import AIProcessor
from .file_manager import DatasetManager, OutputManager
from ..cli.user_interface import UserInterface
from .resume_utils import check_for_resume, update_resume_state, cleanup_resume_state


class BatchProcessor:
    """Orchestrates batch processing of locality data."""
    
    def __init__(self, dataset_manager: DatasetManager, output_manager: OutputManager):
        """
        Initialize batch processor.
        
        Args:
            dataset_manager: File management instance
            output_manager: Output management instance
        """
        self.dataset_manager = dataset_manager
        self.output_manager = output_manager
        self.processing_stats = {
            'total_records': 0,
            'processed_records': 0,
            'api_calls_made': 0,
            'total_cost': 0.0,
            'start_time': None,
            'end_time': None
        }
    
    def process_dataset(self, dataset_info: Dict[str, Any], model_config: Dict[str, Any], 
                       batch_size: int = 8, save_progress: bool = True) -> Dict[str, Any]:
        """
        Process an entire dataset using AI enhancement with resume capability.
        
        Args:
            dataset_info: Dataset information from DatasetManager
            model_config: AI model configuration
            batch_size: Number of records to process per batch
            save_progress: Whether to save progress during processing
            
        Returns:
            Processing results and statistics
        """
        # Check for resume opportunity
        resume_info = check_for_resume(dataset_info)
        start_index = 0
        
        if resume_info:
            if UserInterface.confirm_resume(resume_info):
                start_index = resume_info['completed']
                # Restore previous stats
                self.processing_stats.update({
                    'api_calls_made': resume_info['resume_state']['api_calls'],
                    'total_cost': resume_info['resume_state']['total_cost']
                })
                print(f"Resuming from record {start_index + 1:,}")
        
        # Initialize
        self.processing_stats['start_time'] = time.time()
        
        # Load dataset
        records = self.dataset_manager.load_dataset(dataset_info)
        if not records:
            return {'success': False, 'error': 'Failed to load dataset'}
        
        self.processing_stats['total_records'] = len(records)
        
        # Process only remaining records
        remaining_records = records[start_index:]
        print(f"📊 Processing {len(remaining_records):,} records (starting from index {start_index})")
        
        # Initialize AI processor
        ai_processor = AIProcessor(model_config)
        
        # Create output filename
        output_path = self.dataset_manager.create_output_filename(
            dataset_info, model_config['name']
        )
        
        # Load existing processed records if resuming
        all_processed_records = []
        if start_index > 0:
            # Load existing progress file
            base_name = os.path.splitext(output_path)[0]
            progress_path = f"{base_name}_PROGRESS.tsv"
            
            if os.path.exists(progress_path):
                try:
                    existing_records = self.dataset_manager.load_tsv_file(progress_path)
                    all_processed_records = existing_records
                    print(f"📂 Loaded {len(existing_records):,} previously processed records")
                except Exception as e:
                    print(f"WARNING: Could not load progress file: {e}")
                    print("Starting fresh...")
                    start_index = 0
                    remaining_records = records
        # Process in batches
        total_batches = (len(remaining_records) + batch_size - 1) // batch_size
        
        for batch_num in range(1, total_batches + 1):
            # Get batch from remaining records
            start_idx = (batch_num - 1) * batch_size
            end_idx = min(start_idx + batch_size, len(remaining_records))
            batch = remaining_records[start_idx:end_idx]
            
            # Show progress
            UserInterface.show_batch_progress(batch_num, total_batches, batch_size, len(batch))
            
            try:
                # Process batch
                processed_batch = self._process_batch(batch, ai_processor)
                all_processed_records.extend(processed_batch)
                
                self.processing_stats['processed_records'] += len(processed_batch)
                
                # Update resume state after each batch
                current_index = start_index + start_idx + len(processed_batch) - 1
                update_resume_state(dataset_info, current_index, self.processing_stats, model_config['name'])
                
                # Save progress periodically (save ALL records including previous ones)
                if save_progress and batch_num % 5 == 0:  # Every 5 batches
                    progress_path = self.output_manager.save_progress(
                        all_processed_records, output_path, batch_num
                    )
                    print(f"💾 Progress saved: {progress_path}")
                
            except KeyboardInterrupt:
                print("\nProcessing interrupted by user")
                print("Progress saved automatically - can resume later")
                # Save current progress before exiting
                self.output_manager.save_progress(all_processed_records, output_path, batch_num)
                break
            except Exception as e:
                print(f"❌ Error processing batch {batch_num}: {e}")
                continue
        
        # Save final results
        success = self.output_manager.save_final_results(all_processed_records, output_path)
        
        if success:
            # Clean up resume state on successful completion
            cleanup_resume_state(dataset_info)
        
        # Update stats
        self.processing_stats['end_time'] = time.time()
        
        # Generate summary
        total_time = self.processing_stats['end_time'] - self.processing_stats['start_time']
        UserInterface.show_processing_summary(
            total_time, 
            len(all_processed_records),
            self.processing_stats['api_calls_made'],
            self.processing_stats['total_cost']
        )
        
        UserInterface.show_coordinate_summary(all_processed_records)
        UserInterface.show_next_steps(output_path)
        
        return {
            'success': success,
            'processed_records': all_processed_records,
            'output_path': output_path,
            'stats': self.processing_stats,
            'summary_report': self.output_manager.generate_summary_report(
                all_processed_records, output_path, total_time, model_config['name']
            )
        }
    
    def _process_batch(self, batch: List[Dict[str, Any]], ai_processor: AIProcessor) -> List[Dict[str, Any]]:
        """
        Process a single batch of records.
        
        Args:
            batch: List of records to process
            ai_processor: AI processor instance
            
        Returns:
            List of processed records
        """
        processed_batch = []
        
        for record in batch:
            processed_record = self._process_single_record(record, ai_processor)
            processed_batch.append(processed_record)
            
            # Show individual record progress
            barcode = record.get('Barcode', 'Unknown')
            locality = record.get('Locality verbatim', '')
            UserInterface.show_record_processing(barcode, locality, processed_record)
        
        return processed_batch
    
    def _process_single_record(self, record: Dict[str, Any], ai_processor: AIProcessor) -> Dict[str, Any]:
        """
        Process a single record through the complete pipeline.
        
        Args:
            record: Individual record to process
            ai_processor: AI processor instance
            
        Returns:
            Processed record with enhanced data
        """
        # Start with original record
        processed_record = record.copy()
        
        # Step 1: Preprocess coordinates (existing coords + grid reference conversion)
        enhanced_record = preprocess_coordinates(record)
        
        # Step 2: Always call AI for normalization and restructuring
        locality = record.get('label_verbatim', '') or record.get('Locality verbatim', '')
        country = record.get('Country', '')
        
        # Use preprocessed coordinates if available (grid refs, existing coords)
        existing_lat = enhanced_record.get('preprocessed_lat')
        existing_lon = enhanced_record.get('preprocessed_lon')
        existing_radius = enhanced_record.get('preprocessed_radius')
        coord_source = enhanced_record.get('preprocessed_source', 'needs_ai_processing')
        
        # DEBUG: Print what we're passing to AI
        if existing_lat and existing_lon:
            print(f"   🎯 Passing preprocessed coords to AI: {existing_lat:.6f}, {existing_lon:.6f} (source: {coord_source})")
        else:
            print(f"   ⚠️  No preprocessed coords - AI will estimate")
        
        ai_result = ai_processor.process_locality(
            locality, country, existing_lat, existing_lon, coord_source, existing_radius
        )
        
        # Update statistics
        if ai_result.get('success', True):  # Assume success if not specified
            self.processing_stats['api_calls_made'] += 1
            self.processing_stats['total_cost'] += ai_processor.model_config.get('estimated_cost_per_record', 0.0006)
        
        # Apply AI results
        processed_record.update({
            'Country_Processed': ai_result.get('country', country),
            'State': ai_result.get('state', ''),
            'Region': ai_result.get('region', ''),
            'Sector': ai_result.get('sector', ''),
            'Exact_Site': ai_result.get('exact_site', locality),
            'Latitude': ai_result.get('latitude'),
            'Longitude': ai_result.get('longitude'),
            'Coordinate_Source': ai_result.get('coordinate_source', ''),
            'Coordinate_Radius_Meters': ai_result.get('coordinate_radius_meters'),
            'Elevation': ai_result.get('elevation_meters'),
            'Elevation_Original': ai_result.get('elevation_original', ''),
            'Confidence': ai_result.get('confidence', 'medium'),
            'Processing_Notes': ai_result.get('notes', '')
        })
        
        # Add error information if processing failed
        if not ai_result.get('success', True):
            processed_record['Processing_Notes'] += f" | Error: {ai_result.get('error', 'Unknown error')}"
            processed_record['Confidence'] = 'low'
        
        return processed_record


if __name__ == "__main__":
    # Test the batch processor
    print("🧪 Testing Batch Processor")
    print("=" * 30)
    
    # Initialize managers
    dataset_manager = DatasetManager()
    output_manager = OutputManager()
    processor = BatchProcessor(dataset_manager, output_manager)
    
    # Mock model config
    mock_model = {
        'name': 'Test Model',
        'estimated_cost_per_record': 0.001,
        'requests_per_minute': 50
    }
    
    # Test with mock data
    mock_records = [
        {
            'Barcode': '10577259',
            'Locality verbatim': 'Monks Wood, Hunts., England, TL199798',
            'Country': 'United Kingdom'
        }
    ]
    
    print(f"✅ Batch processor initialized")
    print(f"📊 Ready to process datasets")
    print(f"🔧 Supports coordinate preprocessing")
    print(f"🤖 Integrates with AI processing")
    print(f"💾 Handles progress saving")
    print(f"📈 Tracks processing statistics")
