#!/usr/bin/env python3
"""
PlaceBot Data Directory Setup
==============================

Manages user data directories for PlaceBot.
"""

import os
from pathlib import Path


def get_placebot_home():
    """
    Get PlaceBot's user data directory.

    Returns ``~/.placebot`` so that input/output data live in a writable,
    upgrade-safe location independent of where the package is installed.
    This is required for ``pip install`` to work, since the package itself
    may land in a read-only site-packages directory.

    Set the ``PLACEBOT_HOME`` environment variable to override the location.
    """
    override = os.environ.get('PLACEBOT_HOME')
    if override:
        return Path(override).expanduser()
    return Path.home() / '.placebot'


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
    
    # Create directories (parents=True so ~/.placebot itself is created)
    placebot_home.mkdir(parents=True, exist_ok=True)
    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    batch_jobs_dir.mkdir(parents=True, exist_ok=True)
    
    # Create README in input directory if it doesn't exist
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
  Copy your dataset files to this 'input' folder

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
    
    try:
        # Try to print with emoji
        print("📂 PlaceBot Data Directories")
    except UnicodeEncodeError:
        # Fallback for Windows terminals that don't support emoji
        print("PlaceBot Data Directories")
    
    print("="*70)
    print(f"Home:       {dirs['home']}")
    print(f"Input:      {dirs['input']}")
    print(f"Output:     {dirs['output']}")
    print(f"Batch Jobs: {dirs['batch_jobs']}")
    print()
    print("To add datasets:")
    print(f"   Copy your dataset files to: {dirs['input']}")
    print()


if __name__ == "__main__":
    # For testing - print directory locations
    dirs = setup_directories()
    print(f"PlaceBot directories configured:")
    for key, value in dirs.items():
        print(f"  {key}: {value}")
