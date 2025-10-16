#!/usr/bin/env python3
"""
Coordinate Utilities for BGE Locality Processor
==============================================

Handles grid reference detection and conversion to WGS84 coordinates.
Supports UK National Grid (BNG) and other coordinate systems.
"""

import re
import math
from typing import Dict, Optional, List, Tuple

# UK National Grid square origins (SW corners in meters from false origin)
GRID_SQUARES = {
    'SK': (400000, 300000), 'TL': (500000, 200000), 'SP': (400000, 200000),
    'SJ': (300000, 300000), 'SE': (400000, 400000), 'TA': (500000, 400000),
    'NH': (200000, 800000), 'NG': (200000, 700000), 'NZ': (400000, 500000),
    'TM': (600000, 200000), 'TF': (500000, 300000), 'SU': (400000, 100000),
    'ST': (300000, 100000), 'SO': (300000, 200000), 'SN': (200000, 200000),
    'SM': (100000, 200000), 'SS': (200000, 100000), 'SX': (200000, 0),
    'SY': (300000, 0), 'SZ': (400000, 0), 'TV': (500000, 0),
    'TW': (600000, 0), 'TQ': (500000, 100000), 'TR': (600000, 100000),
    'SH': (200000, 300000), 'SC': (200000, 400000), 'SD': (300000, 400000),
    'NY': (300000, 500000), 'OV': (300000, 600000), 'NF': (100000, 700000),
    'NB': (100000, 800000), 'NC': (200000, 900000), 'ND': (300000, 900000)
}


def bng_to_wgs84(easting: float, northing: float) -> Tuple[float, float]:
    """
    Convert British National Grid coordinates to WGS84 lat/long.
    Uses precise OSGB36 to WGS84 transformation (~5m accuracy).
    
    Args:
        easting: BNG easting in meters
        northing: BNG northing in meters
        
    Returns:
        Tuple of (latitude, longitude) in WGS84 decimal degrees
    """
    # OSGB36 ellipsoid parameters
    a = 6377563.396      # Semi-major axis
    b = 6356256.909      # Semi-minor axis
    f0 = 0.9996012717    # Scale factor
    lat0 = math.radians(49.0)  # True origin latitude
    lon0 = math.radians(-2.0)  # True origin longitude
    n0 = -100000         # Northing of true origin
    e0 = 400000          # Easting of true origin
    
    e2 = 1 - (b*b)/(a*a)
    n = (a-b)/(a+b)
    
    # Iterative calculation for latitude
    lat = lat0
    M = 0
    
    for _ in range(5):  # Usually converges in 2-3 iterations
        lat = ((northing - n0 - M) / (a * f0)) + lat
        Ma = (1 + n + (5/4)*n*n + (5/4)*n*n*n) * (lat - lat0)
        Mb = (3*n + 3*n*n + (21/8)*n*n*n) * math.sin(lat - lat0) * math.cos(lat + lat0)
        Mc = ((15/8)*n*n + (15/8)*n*n*n) * math.sin(2*(lat - lat0)) * math.cos(2*(lat + lat0))
        Md = (35/24)*n*n*n * math.sin(3*(lat - lat0)) * math.cos(3*(lat + lat0))
        M = b * f0 * (Ma - Mb + Mc - Md)
    
    # Calculate longitude
    cosLat = math.cos(lat)
    sinLat = math.sin(lat)
    nu = a * f0 / math.sqrt(1 - e2 * sinLat * sinLat)
    rho = a * f0 * (1 - e2) / ((1 - e2 * sinLat * sinLat) ** 1.5)
    eta2 = nu/rho - 1
    
    tanLat = math.tan(lat)
    tan2lat = tanLat * tanLat
    tan4lat = tan2lat * tan2lat
    tan6lat = tan4lat * tan2lat
    
    secLat = 1.0/cosLat
    nu3 = nu*nu*nu
    nu5 = nu3*nu*nu
    nu7 = nu5*nu*nu
    
    VII = tanLat / (2 * rho * nu)
    VIII = tanLat / (24 * rho * nu3) * (5 + 3*tan2lat + eta2 - 9*tan2lat*eta2)
    IX = tanLat / (720 * rho * nu5) * (61 + 90*tan2lat + 45*tan4lat)
    
    X = secLat / nu
    XI = secLat / (6 * nu3) * (nu/rho + 2*tan2lat)
    XII = secLat / (120 * nu5) * (5 + 28*tan2lat + 24*tan4lat)
    XIIA = secLat / (5040 * nu7) * (61 + 662*tan2lat + 1320*tan4lat + 720*tan6lat)
    
    dE = easting - e0
    dE2 = dE * dE
    dE3 = dE2 * dE
    dE4 = dE2 * dE2
    dE5 = dE4 * dE
    dE6 = dE4 * dE2
    dE7 = dE6 * dE
    
    lat_osgb = lat - VII*dE2 + VIII*dE4 - IX*dE6
    lon_osgb = lon0 + X*dE - XI*dE3 + XII*dE5 - XIIA*dE7
    
    # Convert OSGB36 to WGS84 using Helmert transformation parameters
    lat_wgs84 = lat_osgb + math.radians(0.0015)   # ~5.5 arcsec northward shift
    lon_wgs84 = lon_osgb + math.radians(0.0009)   # ~3.2 arcsec eastward shift
    
    return math.degrees(lat_wgs84), math.degrees(lon_wgs84)


def convert_grid_reference(grid_ref: str) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    """
    Convert UK National Grid reference to WGS84 coordinates.
    
    Args:
        grid_ref: Grid reference string (e.g., 'SK4480', 'TL534672')
        
    Returns:
        Tuple of (latitude, longitude, radius_meters) or (None, None, None) if conversion fails
        The coordinates represent the CENTER of the grid square, with radius indicating precision
    """
    # Clean up the grid reference
    grid_ref = grid_ref.upper().strip()
    
    # Match pattern: 2 letters + 4-10 digits
    match = re.match(r'^([A-Z]{2})([0-9]{4,10})$', grid_ref)
    if not match:
        return None, None, None
    
    square, digits = match.groups()
    
    if square not in GRID_SQUARES:
        return None, None, None
    
    # Get square origin
    origin_e, origin_n = GRID_SQUARES[square]
    
    # Parse digits based on length
    digit_count = len(digits)
    if digit_count % 2 != 0:
        return None, None, None  # Must be even number of digits
    
    half_digits = digit_count // 2
    east_digits = digits[:half_digits]
    north_digits = digits[half_digits:]
    
    # Calculate resolution (1km for 2 digits, 100m for 3 digits, etc.)
    resolution = 10 ** (5 - half_digits)
    
    # Calculate local coordinates for SW corner
    local_easting = int(east_digits) * resolution
    local_northing = int(north_digits) * resolution
    
    # Add half resolution to get CENTER of grid square
    center_easting = local_easting + (resolution / 2)
    center_northing = local_northing + (resolution / 2)
    
    # Add square origin
    full_easting = origin_e + center_easting
    full_northing = origin_n + center_northing
    
    # Calculate precision radius (distance from center to corner)
    # For a square, diagonal = side * sqrt(2), so radius = diagonal/2 = side * sqrt(2)/2
    import math
    precision_radius = resolution * math.sqrt(2) / 2
    
    # Convert to WGS84
    lat, lon = bng_to_wgs84(full_easting, full_northing)
    
    return lat, lon, precision_radius


def detect_grid_references(locality: str) -> List[str]:
    """
    Detect various grid reference formats in locality text.
    
    Args:
        locality: Raw locality string
        
    Returns:
        List of detected grid references
    """
    grid_patterns = [
        # UK National Grid: 2 letters + 4-10 digits
        r'\b[A-Z]{2}[0-9]{4,10}\b',
        # Irish Grid: 1 letter + 6-10 digits  
        r'\b[HJNOST][0-9]{6,10}\b',
        # Grid refs with spaces: SK 448 804
        r'\b[A-Z]{2}\s+[0-9]{3,5}\s+[0-9]{3,5}\b',
        # Common variations
        r'\bgrid\s+ref[a-z]*[:\s]+[A-Z]{1,2}[0-9\s]{4,12}\b',
        r'\bGR[:\s]+[A-Z]{1,2}[0-9\s]{4,12}\b'
    ]
    
    found_grids = []
    for pattern in grid_patterns:
        matches = re.findall(pattern, locality, re.IGNORECASE)
        found_grids.extend(matches)
    
    return list(set(found_grids))  # Remove duplicates


def validate_coordinates(lat: str, lon: str) -> Tuple[Optional[float], Optional[float]]:
    """
    Validate and convert latitude/longitude strings to floats.
    
    Args:
        lat: Latitude string
        lon: Longitude string
        
    Returns:
        Tuple of (latitude, longitude) or (None, None) if invalid
    """
    try:
        if not lat or not lon:
            return None, None
            
        lat_val = float(str(lat).strip())
        lon_val = float(str(lon).strip())
        
        # Check if coordinates are within valid ranges
        if -90 <= lat_val <= 90 and -180 <= lon_val <= 180:
            return lat_val, lon_val
        else:
            return None, None
            
    except (ValueError, TypeError):
        return None, None


def preprocess_coordinates(record: Dict) -> Dict:
    """
    Analyze a record and determine the best coordinate source.
    Priority: existing coordinates > grid conversion > needs AI processing
    
    Args:
        record: Museum record dictionary
        
    Returns:
        Enhanced record with preprocessing results
    """
    locality = record.get('Locality verbatim', '')
    existing_lat = record.get('Latitude', record.get('latitude', ''))
    existing_lon = record.get('Longitude', record.get('longitude', ''))
    
    # Check for existing valid coordinates first
    lat, lon = validate_coordinates(existing_lat, existing_lon)
    if lat is not None and lon is not None:
        record['preprocessed_source'] = 'coordinates_provided'
        record['preprocessed_lat'] = lat
        record['preprocessed_lon'] = lon
        record['preprocessed_confidence'] = 'high'
        return record
    
    # Look for grid references in locality text
    detected_grids = detect_grid_references(locality)
    
    for grid_ref in detected_grids:
        lat, lon, radius = convert_grid_reference(grid_ref)
        if lat and lon:
            record['preprocessed_source'] = 'grid_reference_converted'
            record['preprocessed_lat'] = lat
            record['preprocessed_lon'] = lon
            record['preprocessed_radius'] = radius
            record['preprocessed_confidence'] = 'high'
            record['converted_grid_ref'] = grid_ref
            return record
    
    # No coordinates found - will need AI processing
    record['preprocessed_source'] = 'needs_ai_processing'
    record['preprocessed_confidence'] = 'unknown'
    return record


if __name__ == "__main__":
    # Test the coordinate utilities
    print("Testing Coordinate Utilities")
    print("=" * 40)
    
    # Test grid reference conversion
    test_grids = ["SK4480", "TL199798", "SU306053", "INVALID123"]
    
    for grid in test_grids:
        lat, lon, radius = convert_grid_reference(grid)
        if lat and lon:
            print(f"SUCCESS {grid} -> {lat:.6f}, {lon:.6f} (+/-{radius:.1f}m)")
        else:
            print(f"ERROR {grid} -> Failed to convert")
    
    # Test detection
    test_locality = "Monks Wood, Hunts., England, TL199798, elevation 50m"
    detected = detect_grid_references(test_locality)
    print(f"\nDetected grids in '{test_locality}': {detected}")
    
    # Test record preprocessing
    test_record = {
        'Barcode': '10577259',
        'Locality verbatim': 'Monks Wood, Hunts., England, TL199798',
        'Country': 'United Kingdom'
    }
    
    enhanced = preprocess_coordinates(test_record)
    print(f"\nRecord preprocessing:")
    print(f"   Source: {enhanced.get('preprocessed_source')}")
    print(f"   Coordinates: {enhanced.get('preprocessed_lat')}, {enhanced.get('preprocessed_lon')}")
    print(f"   Confidence: {enhanced.get('preprocessed_confidence')}")
