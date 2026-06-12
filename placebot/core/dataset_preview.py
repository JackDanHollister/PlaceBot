#!/usr/bin/env python3
"""
Dataset Preview for Locality Processor
======================================

Shows sample data and statistics before processing.
"""

from typing import Dict, List, Any
import random


class DatasetPreview:
    """Generates previews and statistics for datasets."""
    
    @staticmethod
    def get_sample_records(data: List[Dict[str, Any]], num_samples: int = 5) -> List[Dict[str, Any]]:
        """
        Get sample records from dataset.
        
        Args:
            data: Full dataset
            num_samples: Number of samples to return
            
        Returns:
            List of sample records
        """
        if len(data) <= num_samples:
            return data
        
        return random.sample(data, num_samples)
    
    @staticmethod
    def get_statistics(data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate statistics about the dataset.
        
        Args:
            data: Dataset records
            
        Returns:
            Dictionary with statistics
        """
        if not data:
            return {
                'total_records': 0,
                'has_data': False
            }
        
        # Basic counts
        total_records = len(data)
        
        # Get all field names (guard against None keys from ragged CSV rows)
        all_fields = set()
        for record in data:
            all_fields.update(k for k in record.keys() if isinstance(k, str))
        
        # Check for coordinate fields (case-insensitive; includes Darwin Core
        # decimalLatitude/decimalLongitude and verbatim variants)
        lowered_fields = {f.lower() for f in all_fields}
        has_lat = any('lat' in f for f in lowered_fields)
        has_lon = any('lon' in f for f in lowered_fields)
        has_coordinates = has_lat and has_lon

        # Check for locality field (native names + Darwin Core verbatimLocality)
        locality_fields = [f for f in all_fields if 'locality' in f.lower() or 'location' in f.lower()]
        has_locality = len(locality_fields) > 0
        
        # Sample locality text length
        if locality_fields:
            sample_texts = [str(record.get(locality_fields[0], '')) 
                          for record in data[:100] if record.get(locality_fields[0])]
            avg_locality_length = sum(len(t) for t in sample_texts) / len(sample_texts) if sample_texts else 0
        else:
            avg_locality_length = 0
        
        return {
            'total_records': total_records,
            'has_data': True,
            'field_count': len(all_fields),
            'field_names': sorted(list(all_fields)),
            'has_coordinates': has_coordinates,
            'has_latitude': has_lat,
            'has_longitude': has_lon,
            'has_locality': has_locality,
            'locality_fields': locality_fields,
            'avg_locality_length': int(avg_locality_length),
            'estimated_size_mb': sum(len(str(v)) for record in data for v in record.values()) / (1024 * 1024)
        }
    
    @staticmethod
    def display_preview(data: List[Dict[str, Any]], num_samples: int = 5):
        """
        Display a formatted preview of the dataset.
        
        Args:
            data: Dataset records
            num_samples: Number of sample records to show
        """
        stats = DatasetPreview.get_statistics(data)
        
        if not stats['has_data']:
            print("❌ No data to preview")
            return
        
        print("\n📊 DATASET PREVIEW")
        print("=" * 70)
        print(f"Total Records: {stats['total_records']:,}")
        print(f"Fields: {stats['field_count']} ({', '.join(stats['field_names'][:5])}" + 
              (f", ... +{stats['field_count']-5} more" if stats['field_count'] > 5 else "") + ")")
        print(f"Estimated Size: {stats['estimated_size_mb']:.2f} MB")
        print(f"Has Coordinates: {'✅ Yes' if stats['has_coordinates'] else '❌ No'}")
        print(f"Has Locality Text: {'✅ Yes' if stats['has_locality'] else '❌ No'}")
        
        if stats['has_locality']:
            print(f"Locality Fields: {', '.join(stats['locality_fields'])}")
            print(f"Avg Locality Length: {stats['avg_locality_length']} characters")
        
        # Show sample records
        print(f"\n📋 SAMPLE RECORDS (showing {min(num_samples, len(data))}):")
        print("-" * 70)
        
        samples = DatasetPreview.get_sample_records(data, num_samples)
        for i, record in enumerate(samples, 1):
            print(f"\nRecord {i}:")
            for key, value in list(record.items())[:5]:  # Show first 5 fields
                value_str = str(value)[:60]  # Truncate long values
                if len(str(value)) > 60:
                    value_str += "..."
                print(f"  {key}: {value_str}")
            if len(record) > 5:
                print(f"  ... +{len(record)-5} more fields")
        
        print("\n" + "=" * 70)
