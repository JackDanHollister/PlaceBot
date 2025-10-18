#!/usr/bin/env python3
"""
File Manager for BGE Locality Processor
======================================

Handles dataset discovery, loading, and output file management.
Supports CSV and TSV formats with automatic delimiter detection.
"""

import csv
import os
from datetime import datetime
from typing import Dict, List, Optional, Any


class DatasetManager:
    """Manages dataset discovery and loading operations."""
    
    def __init__(self, input_folder: str = None, output_folder: str = None):
        if input_folder is None:
            input_folder = os.path.join(os.path.dirname(__file__), '..', 'input')
        if output_folder is None:
            output_folder = os.path.join(os.path.dirname(__file__), '..', 'output')
        self.input_folder = input_folder
        self.output_folder = output_folder
        self._ensure_folders_exist()
    
    def _ensure_folders_exist(self):
        """Create input and output folders if they don't exist."""
        os.makedirs(self.input_folder, exist_ok=True)
        os.makedirs(self.output_folder, exist_ok=True)
    
    def discover_datasets(self) -> List[Dict[str, Any]]:
        """
        Find all CSV/TSV files in the input folder.
        
        Returns:
            List of dataset info dictionaries
        """
        datasets = []
        
        if not os.path.exists(self.input_folder):
            return datasets
        
        for filename in os.listdir(self.input_folder):
            if filename.lower().endswith(('.csv', '.tsv', '.txt')):
                filepath = os.path.join(self.input_folder, filename)
                
                try:
                    dataset_info = self._analyze_dataset(filename, filepath)
                    if dataset_info:
                        datasets.append(dataset_info)
                except Exception as e:
                    print(f"⚠️  Could not analyze {filename}: {e}")
        
        return sorted(datasets, key=lambda x: x['filename'])
    
    def _analyze_dataset(self, filename: str, filepath: str) -> Optional[Dict[str, Any]]:
        """
        Analyze a dataset file to determine format and content.
        
        Args:
            filename: Name of the file
            filepath: Full path to the file
            
        Returns:
            Dataset information dictionary or None if invalid
        """
        try:
            # Read first few lines to analyze
            with open(filepath, 'r', encoding='utf-8') as f:
                first_line = f.readline().strip()
                if not first_line:
                    return None
                
                # Detect delimiter
                delimiter = self._detect_delimiter(first_line)
                
                # Count rows
                f.seek(0)  # Reset to beginning
                row_count = sum(1 for line in f) - 1  # Subtract header
                
                # Get column headers
                f.seek(0)
                reader = csv.DictReader(f, delimiter=delimiter)
                fieldnames = reader.fieldnames or []
                
                # Check for required columns
                has_locality = any('locality' in col.lower() for col in fieldnames)
                has_barcode = any('barcode' in col.lower() or 'id' in col.lower() for col in fieldnames)
                
                return {
                    'filename': filename,
                    'filepath': filepath,
                    'delimiter': delimiter,
                    'row_count': row_count,
                    'columns': fieldnames,
                    'has_locality': has_locality,
                    'has_barcode': has_barcode,
                    'file_size': os.path.getsize(filepath)
                }
                
        except Exception:
            return None
    
    def _detect_delimiter(self, first_line: str) -> str:
        """
        Detect the delimiter used in a CSV/TSV file.
        
        Args:
            first_line: First line of the file
            
        Returns:
            Detected delimiter character
        """
        # Count occurrences of common delimiters
        tab_count = first_line.count('\t')
        comma_count = first_line.count(',')
        pipe_count = first_line.count('|')
        semicolon_count = first_line.count(';')
        
        # Return the most common delimiter
        delimiters = {
            '\t': tab_count,
            ',': comma_count,
            '|': pipe_count,
            ';': semicolon_count
        }
        
        return max(delimiters, key=delimiters.get) if max(delimiters.values()) > 0 else ','
    
    def load_dataset(self, dataset_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Load a dataset from file.
        
        Args:
            dataset_info: Dataset information from discover_datasets()
            
        Returns:
            List of record dictionaries
        """
        records = []
        
        try:
            with open(dataset_info['filepath'], 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f, delimiter=dataset_info['delimiter'])
                records = list(reader)
                
            print(f"📊 Loaded {len(records):,} records from {dataset_info['filename']}")
            return records
            
        except Exception as e:
            print(f"❌ Error loading dataset: {e}")
            return []
    
    def load_tsv_file(self, filepath: str) -> List[Dict[str, Any]]:
        """
        Load records from a TSV file (used for progress files).
        
        Args:
            filepath: Path to TSV file
            
        Returns:
            List of record dictionaries
        """
        try:
            records = []
            with open(filepath, 'r', encoding='utf-8') as f:
                # Use tab delimiter for TSV
                reader = csv.DictReader(f, delimiter='\t')
                
                for row in reader:
                    # Convert numeric fields back to proper types
                    processed_row = {}
                    for key, value in row.items():
                        if value == '':
                            processed_row[key] = None
                        elif key in ['Latitude', 'Longitude', 'Coordinate_Radius_Meters', 'Elevation']:
                            try:
                                processed_row[key] = float(value) if value else None
                            except ValueError:
                                processed_row[key] = value
                        else:
                            processed_row[key] = value
                    
                    records.append(processed_row)
            
            return records
            
        except Exception as e:
            raise Exception(f"Failed to load TSV file {filepath}: {e}")

    def create_output_filename(self, dataset_info: Dict[str, Any], model_name: str, suffix: str = "") -> str:
        """
        Create a timestamped output filename in an organized dated folder.
        
        Args:
            dataset_info: Dataset information
            model_name: Name of the AI model used
            suffix: Optional suffix for the filename
            
        Returns:
            Full path to output file in organized folder structure
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        date_only = datetime.now().strftime("%Y%m%d")
        base_name = os.path.splitext(dataset_info['filename'])[0]
        
        # Clean model name for filename
        model_clean = "".join(c for c in model_name if c.isalnum() or c in ('_', '-')).lower()
        
        # Create organized folder structure: output/YYYYMMDD_dataset_model/
        folder_name = f"{date_only}_{base_name}_{model_clean}"
        output_folder = os.path.join(self.output_folder, folder_name)
        
        # Create the folder if it doesn't exist
        os.makedirs(output_folder, exist_ok=True)
        
        # Build filename parts
        parts = [base_name, model_clean, timestamp]
        if suffix:
            parts.append(suffix)
        
        filename = "_".join(parts) + ".tsv"
        full_path = os.path.join(output_folder, filename)
        
        print(f"📁 Output folder: {folder_name}")
        return full_path


class OutputManager:
    """Manages saving processed results to files."""
    
    @staticmethod
    def save_results(records: List[Dict[str, Any]], output_path: str) -> bool:
        """
        Save processed records to TSV file.
        
        Args:
            records: List of processed record dictionaries
            output_path: Full path to output file
            
        Returns:
            True if successful, False otherwise
        """
        if not records:
            print("⚠️  No records to save")
            return False
        
        try:
            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Get all unique fieldnames from all records
            fieldnames = set()
            for record in records:
                fieldnames.update(record.keys())
            
            # Define desired column order
            desired_order = [
                'Barcode', 'Locality verbatim', 'Country', 'Country_Processed', 
                'Region', 'Sector', 'State', 'Exact_Site', 'Elevation', 
                'Elevation_Original', 'Latitude', 'Longitude', 
                'Coordinate_Radius_Meters', 'Coordinate_Source', 
                'Confidence', 'Processing_Notes'
            ]
            
            # Order fieldnames according to desired order, with any extras at the end
            fieldnames = [col for col in desired_order if col in fieldnames] + \
                         sorted([col for col in fieldnames if col not in desired_order])
            
            # Write TSV file
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter='\t')
                writer.writeheader()
                writer.writerows(records)
            
            print(f"💾 Saved {len(records):,} records to {output_path}")
            return True
            
        except Exception as e:
            print(f"❌ Error saving results: {e}")
            return False
    
    @staticmethod
    def save_progress(records: List[Dict[str, Any]], output_path: str, batch_num: int) -> str:
        """
        Save progress during processing to a single progress file.
        
        Args:
            records: Current processed records
            output_path: Base output path
            batch_num: Current batch number (unused in simple resume)
            
        Returns:
            Path to progress file
        """
        # Create single progress filename (no timestamps)
        base_name = os.path.splitext(output_path)[0]
        progress_path = f"{base_name}_PROGRESS.tsv"
        
        OutputManager.save_results(records, progress_path)
        return progress_path
    
    @staticmethod
    def save_final_results(records: List[Dict[str, Any]], output_path: str) -> bool:
        """
        Save final results and cleanup progress files.
        
        Args:
            records: All processed records
            output_path: Final output path
            
        Returns:
            True if successful, False otherwise
        """
        success = OutputManager.save_results(records, output_path)
        
        if success:
            # Clean up progress file
            try:
                base_name = os.path.splitext(output_path)[0]
                progress_path = f"{base_name}_PROGRESS.tsv"
                
                if os.path.exists(progress_path):
                    os.remove(progress_path)
                    print("Cleaned up progress file")
                    
            except Exception as e:
                print(f"WARNING: Could not cleanup progress file: {e}")
        
        return success

    @staticmethod
    def generate_summary_report(records: List[Dict[str, Any]], output_path: str, processing_time: float, model_name: str) -> str:
        """
        Generate a summary report of processing results.
        
        Args:
            records: Processed records
            output_path: Path where results were saved
            processing_time: Total processing time in seconds
            model_name: Name of AI model used
            
        Returns:
            Summary report as string
        """
        if not records:
            return "No records processed."
        
        total_records = len(records)
        
        # Count coordinate sources
        coord_stats = {
            'coordinates_provided': 0,
            'grid_reference_converted': 0,
            'coordinates_extracted': 0,
            'estimated': 0,
            'no_coordinates': 0
        }
        
        confidence_stats = {
            'high': 0,
            'medium': 0,
            'low': 0,
            'unknown': 0
        }
        
        for record in records:
            coord_source = record.get('Coordinate_Source', 'no_coordinates')
            if coord_source in coord_stats:
                coord_stats[coord_source] += 1
            else:
                coord_stats['no_coordinates'] += 1
            
            confidence = record.get('Confidence', 'unknown')
            if confidence in confidence_stats:
                confidence_stats[confidence] += 1
            else:
                confidence_stats['unknown'] += 1
        
        # Generate report
        report = [
            "📈 PROCESSING SUMMARY REPORT",
            "=" * 50,
            f"📁 Output file: {output_path}",
            f"🤖 AI Model: {model_name}",
            f"📊 Total records: {total_records:,}",
            f"⏱️  Processing time: {processing_time/60:.1f} minutes",
            "",
            "🌍 COORDINATE SOURCES:",
            f"  📍 Existing coordinates: {coord_stats['coordinates_provided']:,}",
            f"  🎯 Grid references converted: {coord_stats['grid_reference_converted']:,}",
            f"  🔍 Coordinates extracted: {coord_stats['coordinates_extracted']:,}",
            f"  🌍 Coordinates estimated: {coord_stats['estimated']:,}",
            f"  ❓ No coordinates: {coord_stats['no_coordinates']:,}",
            "",
            "🎯 CONFIDENCE LEVELS:",
            f"  ⭐ High: {confidence_stats['high']:,} ({confidence_stats['high']/total_records*100:.1f}%)",
            f"  🔶 Medium: {confidence_stats['medium']:,} ({confidence_stats['medium']/total_records*100:.1f}%)",
            f"  🔻 Low: {confidence_stats['low']:,} ({confidence_stats['low']/total_records*100:.1f}%)",
            "",
            "✨ Dataset ready for GIS mapping and research!"
        ]
        
        return "\n".join(report)


if __name__ == "__main__":
    # Test the file management system
    print("🧪 Testing File Management System")
    print("=" * 40)
    
    # Test dataset discovery
    manager = DatasetManager()
    datasets = manager.discover_datasets()
    
    print(f"📂 Found {len(datasets)} dataset(s):")
    for i, dataset in enumerate(datasets, 1):
        print(f"  {i}. {dataset['filename']} ({dataset['row_count']:,} records)")
        print(f"     Delimiter: '{dataset['delimiter']}' | Columns: {len(dataset['columns'])}")
        print(f"     Has locality: {dataset['has_locality']} | Has barcode: {dataset['has_barcode']}")
    
    # Test loading if datasets exist
    if datasets:
        test_dataset = datasets[0]
        print(f"\n📊 Testing load of: {test_dataset['filename']}")
        records = manager.load_dataset(test_dataset)
        
        if records:
            print(f"✅ Loaded {len(records)} records")
            print(f"🔍 Sample record keys: {list(records[0].keys())}")
            
            # Test output filename generation
            output_path = manager.create_output_filename(test_dataset, "Claude 3 Haiku", "test")
            print(f"📁 Output path: {output_path}")
