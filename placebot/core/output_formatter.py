#!/usr/bin/env python3
"""
Output Format Handlers for Locality Processor
=============================================

Supports multiple output formats: CSV, JSON, and GeoJSON.
"""

import io
import json
import csv
from typing import List, Dict, Any

from placebot.core.field_mapping import DWC_COLUMN_ORDER, to_dwc_records


# Canonical output column order, shared by every export path (CLI and GUI;
# single, batch, and staggered processing) so downloads are consistent
# regardless of how they were produced. Any columns not listed here are
# appended afterwards in alphabetical order.
DESIRED_COLUMN_ORDER = [
    'Barcode', 'Locality verbatim', 'Country', 'Country_Processed',
    'State', 'Region', 'Sector', 'Exact_Site', 'Elevation',
    'Elevation_Original', 'Latitude', 'Longitude',
    'Coordinate_Radius_Meters', 'Coordinate_Source',
    'Confidence', 'Processing_Notes',
]

# Keys treated as coordinates (excluded from GeoJSON feature properties).
# Includes the Darwin Core decimal terms so DwC exports drop them from
# properties too.
COORD_KEYS = (
    'Latitude', 'latitude', 'lat', 'Longitude', 'longitude', 'lon', 'long',
    'decimalLatitude', 'decimalLongitude',
)


def order_fieldnames(
    records: List[Dict[str, Any]], priority: List[str] = DESIRED_COLUMN_ORDER
) -> List[str]:
    """Return record field names in the canonical export order.

    Columns in ``priority`` come first (in that order), followed by any
    remaining columns sorted alphabetically. Used everywhere results are
    written so CLI and GUI exports line up exactly. Pass ``DWC_COLUMN_ORDER``
    for Darwin Core exports.
    """
    present = set()
    for record in records:
        present.update(record.keys())
    ordered = [col for col in priority if col in present]
    extras = sorted(col for col in present if col not in priority)
    return ordered + extras


def _prepare(data: List[Dict[str, Any]], dwc: bool):
    """Return (records, fieldnames) ready for writing, applying DwC renaming.

    When ``dwc`` is True the records are copied with their keys renamed to
    Darwin Core terms and ordered by ``DWC_COLUMN_ORDER``; otherwise the native
    records and column order are used unchanged.
    """
    if dwc:
        data = to_dwc_records(data)
        return data, order_fieldnames(data, DWC_COLUMN_ORDER)
    return data, order_fieldnames(data)


class OutputFormatter:
    """Handles conversion of processed data to various output formats."""

    # ------------------------------------------------------------------
    # In-memory byte builders (used by the GUI download/auto-save paths)
    # ------------------------------------------------------------------

    @staticmethod
    def records_to_csv_bytes(data: List[Dict[str, Any]], dwc: bool = False) -> bytes:
        """Render records as CSV bytes with a UTF-8 BOM.

        The BOM (``utf-8-sig``) makes Excel on Windows auto-detect UTF-8 so
        accented names like "Bouches-du-Rhône" render correctly instead of
        mojibake ("Bouches-du-RhÃ´ne"). Set ``dwc`` to rename columns to
        Darwin Core terms.
        """
        if not data:
            return b""
        data, fieldnames = _prepare(data, dwc)
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(data)
        return buf.getvalue().encode("utf-8-sig")

    @staticmethod
    def records_to_tsv_bytes(data: List[Dict[str, Any]], dwc: bool = False) -> bytes:
        """Render records as tab-separated bytes with a UTF-8 BOM.

        Same canonical column order and Excel-friendly BOM as the CSV writer,
        just tab-delimited. Set ``dwc`` to rename columns to Darwin Core terms.
        """
        if not data:
            return b""
        data, fieldnames = _prepare(data, dwc)
        buf = io.StringIO()
        writer = csv.DictWriter(
            buf, fieldnames=fieldnames, extrasaction="ignore", delimiter="\t"
        )
        writer.writeheader()
        writer.writerows(data)
        return buf.getvalue().encode("utf-8-sig")

    @staticmethod
    def records_to_json_bytes(
        data: List[Dict[str, Any]], pretty: bool = True, dwc: bool = False
    ) -> bytes:
        """Render records as UTF-8 JSON bytes.

        Set ``dwc`` to rename keys to Darwin Core terms.
        """
        if dwc:
            data = to_dwc_records(data)
        indent = 2 if pretty else None
        return json.dumps(data, indent=indent, ensure_ascii=False).encode("utf-8")

    @staticmethod
    def build_geojson(data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build a GeoJSON FeatureCollection dict from records."""
        features = []
        for record in data:
            lat = (record.get('Latitude') or record.get('latitude')
                   or record.get('lat') or record.get('decimalLatitude'))
            lon = (record.get('Longitude') or record.get('longitude')
                   or record.get('lon') or record.get('long')
                   or record.get('decimalLongitude'))

            if lat is None or lon is None or lat == '' or lon == '':
                continue
            try:
                lat_float = float(lat)
                lon_float = float(lon)
            except (ValueError, TypeError):
                continue

            properties = {k: v for k, v in record.items() if k not in COORD_KEYS}
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [lon_float, lat_float],  # GeoJSON is [lon, lat]
                },
                "properties": properties,
            })
        return {"type": "FeatureCollection", "features": features}

    @staticmethod
    def records_to_geojson_bytes(data: List[Dict[str, Any]], dwc: bool = False) -> bytes:
        """Render records as UTF-8 GeoJSON bytes.

        Set ``dwc`` to rename feature properties to Darwin Core terms.
        """
        if dwc:
            data = to_dwc_records(data)
        geojson = OutputFormatter.build_geojson(data)
        return json.dumps(geojson, indent=2, ensure_ascii=False).encode("utf-8")

    # ------------------------------------------------------------------
    # File writers
    # ------------------------------------------------------------------

    @staticmethod
    def to_csv(data: List[Dict[str, Any]], output_path: str, dwc: bool = False) -> str:
        """
        Write data to CSV format.

        Args:
            data: List of record dictionaries
            output_path: Output file path
            dwc: Rename columns to Darwin Core terms

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

        # Written as bytes (with BOM) so the file matches the GUI download byte
        # for byte and Excel renders accents correctly.
        with open(output_path, 'wb') as f:
            f.write(OutputFormatter.records_to_csv_bytes(data, dwc=dwc))

        return output_path

    @staticmethod
    def to_tsv(data: List[Dict[str, Any]], output_path: str, dwc: bool = False) -> str:
        """
        Write data to TSV (tab-separated) format.

        Args:
            data: List of record dictionaries
            output_path: Output file path
            dwc: Rename columns to Darwin Core terms

        Returns:
            Path to created file
        """
        if not data:
            raise ValueError("No data to write")

        # Ensure .tsv extension (append, don't use with_suffix - model names like
        # "Gemini 3.1 Pro" contain dots that with_suffix would truncate)
        output_path = str(output_path)
        if not output_path.lower().endswith('.tsv'):
            output_path += '.tsv'

        with open(output_path, 'wb') as f:
            f.write(OutputFormatter.records_to_tsv_bytes(data, dwc=dwc))

        return output_path

    @staticmethod
    def to_json(
        data: List[Dict[str, Any]], output_path: str, pretty: bool = True, dwc: bool = False
    ) -> str:
        """
        Write data to JSON format.

        Args:
            data: List of record dictionaries
            output_path: Output file path
            pretty: Whether to pretty-print JSON
            dwc: Rename keys to Darwin Core terms

        Returns:
            Path to created file
        """
        # Ensure .json extension (append, don't use with_suffix - model names like
        # "Gemini 3.1 Pro" contain dots that with_suffix would truncate)
        output_path = str(output_path)
        if not output_path.lower().endswith('.json'):
            output_path += '.json'

        with open(output_path, 'wb') as f:
            f.write(OutputFormatter.records_to_json_bytes(data, pretty=pretty, dwc=dwc))

        return output_path
    
    @staticmethod
    def to_geojson(data: List[Dict[str, Any]], output_path: str, dwc: bool = False) -> str:
        """
        Write data to GeoJSON format.

        Args:
            data: List of record dictionaries with latitude/longitude
            output_path: Output file path
            dwc: Rename feature properties to Darwin Core terms

        Returns:
            Path to created file
        """
        # Ensure .geojson extension (append, don't use with_suffix - model names
        # like "Gemini 3.1 Pro" contain dots that with_suffix would truncate)
        output_path = str(output_path)
        if not output_path.lower().endswith('.geojson'):
            output_path += '.geojson'

        with open(output_path, 'wb') as f:
            f.write(OutputFormatter.records_to_geojson_bytes(data, dwc=dwc))

        return output_path

    @staticmethod
    def write_output(
        data: List[Dict[str, Any]], base_path: str, formats: List[str], dwc: bool = False
    ) -> Dict[str, str]:
        """
        Write output in multiple formats.

        Args:
            data: List of record dictionaries
            base_path: Base output path (without extension)
            formats: List of format names ('csv', 'json', 'geojson')
            dwc: Rename columns/keys to Darwin Core terms in every export

        Returns:
            Dictionary mapping format names to output paths
        """
        results = {}

        for fmt in formats:
            fmt_lower = fmt.lower()
            try:
                if fmt_lower == 'csv':
                    path = OutputFormatter.to_csv(data, base_path, dwc=dwc)
                    results['csv'] = path
                elif fmt_lower == 'tsv':
                    path = OutputFormatter.to_tsv(data, base_path, dwc=dwc)
                    results['tsv'] = path
                elif fmt_lower == 'json':
                    path = OutputFormatter.to_json(data, base_path, dwc=dwc)
                    results['json'] = path
                elif fmt_lower == 'geojson':
                    path = OutputFormatter.to_geojson(data, base_path, dwc=dwc)
                    results['geojson'] = path
                else:
                    print(f"⚠️  Unknown format: {fmt}")
            except Exception as e:
                print(f"❌ Error writing {fmt_lower}: {e}")

        return results
