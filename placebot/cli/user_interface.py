#!/usr/bin/env python3
"""
User Interface
==============

Handles all interactive user prompts and progress display.
Provides a user-friendly command-line interface.
"""

import time
from typing import Dict, List, Optional, Any


class UserInterface:
    """Handles all user interactions and display formatting."""
    
    @staticmethod
    def show_welcome():
        """Display welcome message and program information."""
        print("🌍 PLACEBOT — LOCALITY DATASET PROCESSOR")
        print("=" * 50)
        print("📍 Interactive tool for cleaning museum locality data")
        print("🤖 Uses AI to enhance coordinates and geographic information")
        print("🎯 Converts grid references to precise WGS84 coordinates")
        print()
    
    @staticmethod
    def display_datasets(datasets: List[Dict[str, Any]]) -> None:
        """
        Display available datasets in a formatted table.
        
        Args:
            datasets: List of dataset information dictionaries
        """
        if not datasets:
            print("❌ No datasets found in the input folder!")
            print("💡 Please add CSV or TSV files to the 'input' folder.")
            return
        
        print("📊 AVAILABLE DATASETS:")
        print("-" * 70)
        
        for i, dataset in enumerate(datasets, 1):
            # Format file size
            size_mb = dataset['file_size'] / (1024 * 1024)
            size_str = f"{size_mb:.1f}MB" if size_mb >= 1 else f"{dataset['file_size']/1024:.0f}KB"
            
            # Determine file type
            delimiter_name = {'\t': 'TSV', ',': 'CSV', '|': 'PSV', ';': 'SSV'}.get(dataset['delimiter'], 'TXT')
            
            print(f"{i:2d}. {dataset['filename']}")
            print(f"     📋 {dataset['row_count']:,} records | 📁 {size_str} | 📄 {delimiter_name}")
            print(f"     📍 Locality: {'✅' if dataset['has_locality'] else '❌'} | 🏷️  ID: {'✅' if dataset['has_barcode'] else '❌'}")
            
            # Show some column names
            cols_display = ", ".join(dataset['columns'][:4])
            if len(dataset['columns']) > 4:
                cols_display += f" + {len(dataset['columns'])-4} more"
            print(f"     📊 Columns: {cols_display}")
            print()
    
    @staticmethod
    def select_dataset(datasets: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Interactive dataset selection.
        
        Args:
            datasets: List of available datasets
            
        Returns:
            Selected dataset info or None if cancelled
        """
        UserInterface.display_datasets(datasets)
        
        if not datasets:
            return None
        
        while True:
            try:
                choice = input(f"🔢 Select dataset (1-{len(datasets)}) or 'q' to quit: ").strip().lower()
                
                if choice == 'q':
                    print("❌ Dataset selection cancelled")
                    return None
                
                choice_num = int(choice)
                if 1 <= choice_num <= len(datasets):
                    selected = datasets[choice_num - 1]
                    print(f"✅ Selected: {selected['filename']}")
                    return selected
                else:
                    print(f"❌ Please enter a number between 1 and {len(datasets)}")
                    
            except ValueError:
                print("❌ Please enter a valid number or 'q' to quit")
            except KeyboardInterrupt:
                print("\n❌ Selection cancelled")
                return None
    
    @staticmethod
    def get_batch_size(default: int = 8) -> int:
        """
        Get batch size from user with validation.
        
        Args:
            default: Default batch size
            
        Returns:
            Validated batch size
        """
        print(f"\n📦 BATCH SIZE CONFIGURATION")
        print(f"💡 Batch size determines how many records are processed together")
        print(f"⚡ Smaller batches = more reliable, larger batches = faster")
        print(f"🎯 Recommended: 5-15 records per batch")
        
        while True:
            try:
                user_input = input(f"\n🔢 Enter batch size (default {default}): ").strip()
                
                if not user_input:
                    print(f"✅ Using default batch size: {default}")
                    return default
                
                batch_size = int(user_input)
                if 1 <= batch_size <= 50:
                    print(f"✅ Batch size set to: {batch_size}")
                    return batch_size
                else:
                    print("❌ Batch size must be between 1 and 50")
                    
            except ValueError:
                print("❌ Please enter a valid number")
            except KeyboardInterrupt:
                print(f"\n💡 Using default batch size: {default}")
                return default
    
    @staticmethod
    def confirm_resume(resume_info: Dict[str, Any]) -> bool:
        """
        Confirm whether user wants to resume previous processing session.
        
        Args:
            resume_info: Resume information from check_for_resume()
            
        Returns:
            True if user chooses to resume, False otherwise
        """
        print(f"\n⏸️  PREVIOUS SESSION FOUND")
        print("=" * 40)
        print(f"✅ Completed: {resume_info['completed']:,} records ({resume_info['progress_percent']:.1f}%)")
        print(f"⏳ Remaining: {resume_info['remaining']:,} records")
        print(f"💰 Cost so far: ${resume_info['resume_state']['total_cost']:.4f}")
        print(f"🤖 Model: {resume_info['resume_state']['model_name']}")
        
        print(f"\nOptions:")
        print(f"[1] Resume from record {resume_info['completed'] + 1:,} ✨ (recommended)")
        print(f"[2] Start over (lose progress)")
        
        while True:
            try:
                choice = input("Select option (1-2): ").strip()
                
                if choice == '1':
                    print(f"✅ Resuming from record {resume_info['completed'] + 1:,}")
                    return True
                elif choice == '2':
                    confirm = input("⚠️  This will lose all progress. Are you sure? (y/n): ").strip().lower()
                    if confirm == 'y':
                        print("🔄 Starting fresh processing")
                        return False
                else:
                    print("Please enter 1 or 2")
                    
            except KeyboardInterrupt:
                print("\nResume cancelled.")
                return False

    @staticmethod
    def confirm_processing(dataset_info: Dict[str, Any], model_info: Dict[str, Any], batch_size: int) -> bool:
        """
        Show final confirmation before processing starts.
        
        Args:
            dataset_info: Selected dataset information
            model_info: Selected AI model information
            batch_size: Chosen batch size
            
        Returns:
            True if user confirms, False otherwise
        """
        print(f"\n🎯 PROCESSING CONFIGURATION")
        print("-" * 40)
        print(f"📁 Dataset: {dataset_info['filename']}")
        print(f"📊 Records: {dataset_info['row_count']:,}")
        print(f"🤖 AI Model: {model_info['name']}")
        print(f"📦 Batch size: {batch_size}")
        
        # Calculate estimated batches and time
        num_batches = (dataset_info['row_count'] + batch_size - 1) // batch_size
        est_time_minutes = num_batches * (60 / model_info.get('requests_per_minute', 50))
        
        print(f"⚡ Estimated batches: {num_batches}")
        print(f"⏱️  Estimated time: {est_time_minutes:.1f} minutes")
        
        print(f"\n💡 You can stop processing anytime with Ctrl+C")
        
        while True:
            try:
                confirm = input(f"\n❓ Start processing? (y/n): ").strip().lower()
                if confirm in ['y', 'yes']:
                    return True
                elif confirm in ['n', 'no']:
                    print("❌ Processing cancelled")
                    return False
                else:
                    print("❌ Please enter 'y' for yes or 'n' for no")
            except KeyboardInterrupt:
                print("\n❌ Processing cancelled")
                return False
    
    @staticmethod
    def show_batch_progress(batch_num: int, total_batches: int, batch_size: int, records_in_batch: int):
        """
        Display batch processing progress.
        
        Args:
            batch_num: Current batch number
            total_batches: Total number of batches
            batch_size: Expected batch size
            records_in_batch: Actual records in this batch
        """
        progress_percent = (batch_num / total_batches) * 100
        print(f"\n⚡ Processing batch {batch_num}/{total_batches} ({progress_percent:.1f}%)")
        print(f"📦 {records_in_batch} records in this batch")
    
    @staticmethod
    def show_record_processing(barcode: str, locality: str, processing_result: Dict[str, Any]):
        """
        Display individual record processing results.
        
        Args:
            barcode: Record barcode/ID
            locality: Original locality text
            processing_result: Results from processing
        """
        # Truncate long locality strings
        display_locality = locality[:50] + "..." if len(locality) > 50 else locality
        
        print(f"  🔍 {barcode}: {display_locality}")
        
        # FIXED: Check for coordinates using the correct field names from batch_processor output
        lat = processing_result.get('Latitude')
        lon = processing_result.get('Longitude')
        coord_source = processing_result.get('Coordinate_Source', '')
        
        if lat and lon:
            source_icons = {
                'coordinates_provided': '✅',
                'grid_reference_converted': '🎯',
                'coordinates_extracted': '🔍',
                'estimated': '🌍'
            }
            
            icon = source_icons.get(coord_source, '📍')
            print(f"     {icon} {lat:.6f}, {lon:.6f} ({coord_source})")
            
            # Show grid reference info if available
            if coord_source == 'grid_reference_converted':
                notes = processing_result.get('Processing_Notes', '')
                if 'grid reference:' in notes:
                    grid_ref = notes.split('grid reference: ')[-1].strip()
                    print(f"     🎯 Converted from grid reference: {grid_ref}")
            
            # Show radius for estimates
            radius = processing_result.get('Coordinate_Radius_Meters')
            if radius and coord_source == 'estimated':
                print(f"     📍 Estimated radius: {radius}m")
                
        else:
            print(f"     ❓ No coordinates found")
    
    @staticmethod
    def show_processing_summary(total_time: float, total_records: int, api_calls: int, cost: float):
        """
        Display final processing summary.
        
        Args:
            total_time: Total processing time in seconds
            total_records: Number of records processed
            api_calls: Number of API calls made
            cost: Total estimated cost
        """
        print(f"\n🎉 PROCESSING COMPLETE!")
        print("=" * 50)
        print(f"📊 Records processed: {total_records:,}")
        print(f"⚡ API calls made: {api_calls:,}")
        print(f"⏱️  Total time: {total_time/60:.1f} minutes")
        print(f"💰 Estimated cost: ${cost:.4f}")
        
        if total_time > 0:
            rate = total_records / total_time * 60
            print(f"📈 Processing rate: {rate:.1f} records/minute")
    
    @staticmethod
    def show_coordinate_summary(records: List[Dict[str, Any]]):
        """
        Display summary of coordinate processing results.
        
        Args:
            records: List of processed records
        """
        if not records:
            return
        
        # Count coordinate sources using the correct field names
        source_counts = {}
        confidence_counts = {}
        
        for record in records:
            source = record.get('Coordinate_Source', 'no_coordinates')
            confidence = record.get('Confidence', 'unknown')
            
            source_counts[source] = source_counts.get(source, 0) + 1
            confidence_counts[confidence] = confidence_counts.get(confidence, 0) + 1
        
        print(f"\n📍 COORDINATE PROCESSING RESULTS:")
        for source, count in source_counts.items():
            percentage = (count / len(records)) * 100
            icon = {'coordinates_provided': '✅', 'grid_reference_converted': '🎯', 
                   'coordinates_extracted': '🔍', 'estimated': '🌍', 'no_coordinates': '❓'}.get(source, '📍')
            print(f"  {icon} {source.replace('_', ' ').title()}: {count:,} ({percentage:.1f}%)")
        
        print(f"\n🎯 CONFIDENCE LEVELS:")
        for confidence, count in confidence_counts.items():
            percentage = (count / len(records)) * 100
            icon = {'high': '⭐', 'medium': '🔶', 'low': '🔻', 'unknown': '❓'}.get(confidence, '📊')
            print(f"  {icon} {confidence.title()}: {count:,} ({percentage:.1f}%)")
    
    @staticmethod
    def show_next_steps(output_path: str):
        """
        Display suggested next steps after processing.
        
        Args:
            output_path: Path to the output file
        """
        print(f"\n💡 NEXT STEPS:")
        print(f"📂 Your processed data: {output_path}")
        print(f"🗺️  Open in GIS software (QGIS, ArcGIS)")
        print(f"📊 Import to spreadsheet (Excel, Google Sheets)")
        print(f"🌍 Use Latitude/Longitude columns for mapping")
        print(f"🎯 Check Confidence column for data quality")
        print(f"📝 Review Processing_Notes for details")
        print(f"\n✨ Your data is now ready for research and analysis!")
    
    @staticmethod
    def prompt_processing_mode() -> str:
        """
        Ask user to choose processing mode.
        
        Returns:
            'realtime', 'batch', or 'staggered'
        """
        print("\n⚡ PROCESSING MODE SELECTION")
        print("=" * 50)
        print("1. Real-time Processing")
        print("   • Get results immediately")
        print("   • Process records as they complete")
        print("   • Best for: Small datasets (<1000 records)")
        print()
        print("2. Batch Processing (50% cost savings!)")
        print("   • Results delivered within 24 hours")
        print("   • Much cheaper ($)")
        print("   • Best for: Large datasets (1000+ records)")
        print()
        print("3. Staggered Batch (50% cost savings + quota-safe!)")
        print("   • Splits into smaller batches automatically")
        print("   • Avoids quota limits on large datasets")
        print("   • Best for: Very large datasets (3000+ records)")
        print("   • Recommended for Gemini API")
        print()
        
        while True:
            choice = input("Choose mode (1 for realtime, 2 for batch, 3 for staggered): ").strip()
            if choice == '1':
                return 'realtime'
            elif choice == '2':
                return 'batch'
            elif choice == '3':
                return 'staggered'
            else:
                print("❌ Please enter 1, 2, or 3")
    
    @staticmethod
    def prompt_output_formats() -> List[str]:
        """
        Ask user to choose output formats.
        
        Returns:
            List of format names
        """
        print("\n📁 OUTPUT FORMAT SELECTION")
        print("=" * 50)
        print("Available formats:")
        print("1. CSV (spreadsheet-friendly)")
        print("2. JSON (programming-friendly)")
        print("3. GeoJSON (GIS software compatible)")
        print("4. All formats")
        print()
        
        choice = input("Choose formats (1-4, or comma-separated like '1,3'): ").strip()
        
        if choice == '4':
            return ['csv', 'json', 'geojson']
        else:
            formats = []
            for c in choice.split(','):
                c = c.strip()
                if c == '1':
                    formats.append('csv')
                elif c == '2':
                    formats.append('json')
                elif c == '3':
                    formats.append('geojson')
            
            return formats if formats else ['csv']  # Default to CSV

    @staticmethod
    def prompt_dwc_output() -> bool:
        """Ask whether output columns should use Darwin Core (DwC) terms.

        Returns:
            True if the user wants Darwin Core column names in the exports.
        """
        print("\n🧬 DARWIN CORE (DwC) OUTPUT")
        print("=" * 50)
        print("Rename output columns to Darwin Core terms (dwc.tdwg.org)?")
        print("e.g. Latitude -> decimalLatitude, Exact_Site -> locality.")
        choice = input("Use Darwin Core output terms? (y/N): ").strip().lower()
        return choice in ('y', 'yes')

    @staticmethod
    def prompt_deduplicate() -> bool:
        """Ask whether to deduplicate repeated localities before processing.

        Returns:
            True if the user wants deduplication enabled (the default).
        """
        print("\n♻️  DEDUPLICATION")
        print("=" * 50)
        print("Collapse repeated locality/country records before processing?")
        print("Each unique place is georeferenced once, then the result is")
        print("re-expanded onto every original record (saves time and cost).")
        choice = input("Deduplicate repeated localities? (Y/n): ").strip().lower()
        return choice not in ('n', 'no')


if __name__ == "__main__":
    # Test the user interface
    print("🧪 Testing User Interface - FIXED VERSION")
    print("=" * 40)
    
    # Test welcome
    UserInterface.show_welcome()
    
    # Test dataset display with mock data
    mock_datasets = [
        {
            'filename': 'test_data.tsv',
            'row_count': 1250,
            'file_size': 524288,  # 512KB
            'delimiter': '\t',
            'has_locality': True,
            'has_barcode': True,
            'columns': ['Barcode', 'Locality verbatim', 'Country', 'Latitude', 'Longitude']
        }
    ]
    
    UserInterface.display_datasets(mock_datasets)
    
    # Test processing summary with mock data - USING CORRECT FIELD NAMES
    mock_records = [
        {'Coordinate_Source': 'grid_reference_converted', 'Confidence': 'high'},
        {'Coordinate_Source': 'coordinates_provided', 'Confidence': 'high'},
        {'Coordinate_Source': 'estimated', 'Confidence': 'medium'}
    ]
    
    UserInterface.show_coordinate_summary(mock_records)
