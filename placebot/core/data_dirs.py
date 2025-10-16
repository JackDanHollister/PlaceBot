#!/usr/bin/env python3
"""
PlaceBot Data Directory Setup
==============================

Manages user data directories for PlaceBot.
"""

import os
from pathlib import Path


def get_placebot_home():
    """Get PlaceBot's data directory in user's home folder."""
    home = Path.home()
    placebot_dir = home / '.placebot'
    return placebot_dir


def get_input_dir():
    """Get input directory for datasets."""
    return get_placebot_home() / 'input'


def get_output_dir():
    """Get output directory for results."""
    return get_placebot_home() / 'output'


def get_batch_jobs_dir():
    """Get directory for batch job tracking."""
    return get_output_dir() / 'batch_jobs'


def setup_directories():
    """Create PlaceBot data directories if they don't exist."""
    placebot_home = get_placebot_home()
    input_dir = get_input_dir()
    output_dir = get_output_dir()
    batch_jobs_dir = get_batch_jobs_dir()
    
    # Create directories
    placebot_home.mkdir(exist_ok=True)
    input_dir.mkdir(exist_ok=True)
    output_dir.mkdir(exist_ok=True)
    batch_jobs_dir.mkdir(exist_ok=True)
    
    # Create README in input directory
    readme_file = input_dir / 'README.txt'
    if not readme_file.exists():
        with open(readme_file, 'w') as f:
            f.write("""PlaceBot Input Directory
========================

Put your datasets here!

Supported formats:
- CSV (.csv)
- TSV (.tsv)
- Excel (.xlsx)

Required columns:
- ID column: Barcode, ID, Record_ID (or similar)
- Locality column: Locality verbatim, label_verbatim, Locality (or similar)

Optional columns:
- Country
- lat_manual, lon_manual (for comparison)

Example:
  cp ~/my_dataset.csv ~/.placebot/input/

Then run:
  placebot

Your dataset will appear in the menu automatically!
""")
    
    return {
        'home': str(placebot_home),
        'input': str(input_dir),
        'output': str(output_dir),
        'batch_jobs': str(batch_jobs_dir)
    }


def show_directory_info():
    """Display PlaceBot directory information."""
    dirs = setup_directories()
    
    print("📂 PlaceBot Data Directories")
    print("="*70)
    print(f"Home:       {dirs['home']}")
    print(f"Input:      {dirs['input']}")
    print(f"Output:     {dirs['output']}")
    print(f"Batch Jobs: {dirs['batch_jobs']}")
    print()
    print("💡 To add datasets:")
    print(f"   cp your_dataset.csv {dirs['input']}/")
    print()


if __name__ == '__main__':
    show_directory_info()
