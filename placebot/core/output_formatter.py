#!/usr/bin/env python3
"""
Output Format Handlers for Locality Processor
=============================================

Supports multiple output formats: CSV, JSON, and GeoJSON.
"""

import json
import csv
from typing import List, Dict, Any
from pathlib import Path


class OutputFormatter:
    """Handles conversion of processed data to various output formats."""
    
    @staticmethod
    def to_csv(data: List[Dict[str, Any]], output_path: str) -> str:
        """
        Write data to CSV format.
        
        Args:
            data: List of record dictionaries
            output_path: Output file path
            
        Returns:
            Path to created file
        """
        if not data:
            raise ValueError("No data to write")
        
        # Ensure .csv extension (append, don't use with_suffix - model names like
        # "Gemini 3.1 Pro" contain dots that with_suffix would truncate)
        output_path = str(output_path)
        if not output_path.lower().endswith('.csv'):
            output_path += '.csv'
        
        # Get all unique keys from all records
        fieldnames = set()
        for record in data:
            fieldnames.update(record.keys())
        
        # Define desired column order
        desired_order = [
            'Barcode', 'Locality verbatim', 'Country', 'Country_Processed', 
            'State', 'Region', 'Sector', 'Exact_Site', 'Elevation', 
            'Elevation_Original', 'Latitude', 'Longitude', 
            'Coordinate_Radius_Meters', 'Coordinate_Source', 
            'Confidence', 'Processing_Notes'
        ]
        
        # Order fieldnames according to desired order, with any extras at the end
        fieldnames = [col for col in desired_order if col in fieldnames] + \
                     sorted([col for col in fieldnames if col not in desired_order])
        
        # Write CSV with a UTF-8 BOM (utf-8-sig) so Excel on Windows auto-detects
        # the encoding and shows accented locality names (e.g. "Rhône") correctly
        # instead of mojibake ("RhÃ´ne").
        with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
        
        return output_path
    
    @staticmethod
    def to_json(data: List[Dict[str, Any]], output_path: str, pretty: bool = True) -> str:
        """
        Write data to JSON format.
        
        Args:
            data: List of record dictionaries
            output_path: Output file path
            pretty: Whether to pretty-print JSON
            
        Returns:
            Path to created file
        """
        # Ensure .json extension (append, don't use with_suffix - model names like
        # "Gemini 3.1 Pro" contain dots that with_suffix would truncate)
        output_path = str(output_path)
        if not output_path.lower().endswith('.json'):
            output_path += '.json'
        
        with open(output_path, 'w', encoding='utf-8') as f:
            if pretty:
                json.dump(data, f, indent=2, ensure_ascii=False)
            else:
                json.dump(data, f, ensure_ascii=False)
        
        return output_path
    
    @staticmethod
    def to_geojson(data: List[Dict[str, Any]], output_path: str) -> str:
        """
        Write data to GeoJSON format.
        
        Args:
            data: List of record dictionaries with latitude/longitude
            output_path: Output file path
            
        Returns:
            Path to created file
        """
        # Ensure .geojson extension (append, don't use with_suffix - model names
        # like "Gemini 3.1 Pro" contain dots that with_suffix would truncate)
        output_path = str(output_path)
        if not output_path.lower().endswith('.geojson'):
            output_path += '.geojson'
        
        coord_keys = ('Latitude', 'latitude', 'lat', 'Longitude', 'longitude', 'lon', 'long')
        features = []
        for record in data:
            # Extract coordinates (handle both capitalised and lowercase keys)
            lat = record.get('Latitude') or record.get('latitude') or record.get('lat')
            lon = (record.get('Longitude') or record.get('longitude')
                   or record.get('lon') or record.get('long'))

            # Skip records without valid coordinates
            if lat is None or lon is None or lat == '' or lon == '':
                continue

            try:
                lat_float = float(lat)
                lon_float = float(lon)
            except (ValueError, TypeError):
                continue

            # Create properties (all fields except coordinates)
            properties = {k: v for k, v in record.items() if k not in coord_keys}
            
            # Create GeoJSON feature
            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [lon_float, lat_float]  # GeoJSON is [lon, lat]
                },
                "properties": properties
            }
            features.append(feature)
        
        # Create GeoJSON FeatureCollection
        geojson = {
            "type": "FeatureCollection",
            "features": features
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(geojson, f, indent=2, ensure_ascii=False)
        
        return output_path
    
    @staticmethod
    def write_output(data: List[Dict[str, Any]], base_path: str, formats: List[str]) -> Dict[str, str]:
        """
        Write output in multiple formats.
        
        Args:
            data: List of record dictionaries
            base_path: Base output path (without extension)
            formats: List of format names ('csv', 'json', 'geojson')
            
        Returns:
            Dictionary mapping format names to output paths
        """
        results = {}
        
        for fmt in formats:
            fmt_lower = fmt.lower()
            try:
                if fmt_lower == 'csv':
                    path = OutputFormatter.to_csv(data, base_path)
                    results['csv'] = path
                elif fmt_lower == 'json':
                    path = OutputFormatter.to_json(data, base_path)
                    results['json'] = path
                elif fmt_lower == 'geojson':
                    path = OutputFormatter.to_geojson(data, base_path)
                    results['geojson'] = path
                else:
                    print(f"⚠️  Unknown format: {fmt}")
            except Exception as e:
                print(f"❌ Error writing {fmt_lower}: {e}")
        
        return results
