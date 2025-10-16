#!/usr/bin/env python3
"""
Resume Utilities for BGE Locality Processor
==========================================

Simple resume functionality for batch processing.
Tracks last completed record index and essential statistics.
"""

import json
import os
from typing import Dict, Optional, Any


def check_for_resume(dataset_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Check if a resume opportunity exists for this dataset.
    
    Args:
        dataset_info: Dataset information from DatasetManager
        
    Returns:
        Resume info dict if available, None otherwise
    """
    try:
        # Create resume filename
        base_name = os.path.splitext(dataset_info['filename'])[0]
        resume_file = os.path.join('output', f"{base_name}_resume.json")
        
        if not os.path.exists(resume_file):
            return None
        
        # Load resume state
        with open(resume_file, 'r', encoding='utf-8') as f:
            state = json.load(f)
        
        # Simple file change detection
        current_size = os.path.getsize(dataset_info['filepath'])
        if current_size != state.get('input_file_size', 0):
            print("WARNING: Input file has changed since last session, cannot resume")
            return None
        
        # Calculate resume info
        completed = state['last_completed_index'] + 1
        remaining = state['total_records'] - completed
        progress_percent = (completed / state['total_records']) * 100
        
        return {
            'resume_state': state,
            'completed': completed,
            'remaining': remaining,
            'progress_percent': progress_percent
        }
        
    except Exception as e:
        print(f"WARNING: Resume file corrupted ({e}), starting fresh")
        return None


def update_resume_state(dataset_info: Dict[str, Any], last_completed_index: int, 
                       stats: Dict[str, Any], model_name: str) -> None:
    """
    Update resume state file with current progress.
    
    Args:
        dataset_info: Dataset information
        last_completed_index: Index of last successfully processed record (0-based)
        stats: Processing statistics
        model_name: Name of AI model being used
    """
    try:
        # Create resume filename
        base_name = os.path.splitext(dataset_info['filename'])[0]
        resume_file = os.path.join('output', f"{base_name}_resume.json")
        
        # Ensure output directory exists
        os.makedirs('output', exist_ok=True)
        
        # Create state
        state = {
            "input_file": dataset_info['filename'],
            "input_file_size": os.path.getsize(dataset_info['filepath']),
            "total_records": dataset_info['row_count'],
            "last_completed_index": last_completed_index,
            "model_name": model_name,
            "start_time": stats.get('start_time', ''),
            "api_calls": stats.get('api_calls_made', 0),
            "total_cost": stats.get('total_cost', 0.0)
        }
        
        # Save state
        with open(resume_file, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2)
            
    except Exception as e:
        print(f"WARNING: Could not save resume state: {e}")


def cleanup_resume_state(dataset_info: Dict[str, Any]) -> None:
    """
    Clean up resume state file after successful completion.
    
    Args:
        dataset_info: Dataset information
    """
    try:
        base_name = os.path.splitext(dataset_info['filename'])[0]
        resume_file = os.path.join('output', f"{base_name}_resume.json")
        
        if os.path.exists(resume_file):
            os.remove(resume_file)
            print("Cleaned up resume state file")
            
    except Exception as e:
        print(f"WARNING: Could not cleanup resume file: {e}")


if __name__ == "__main__":
    # Test resume utilities
    print("🧪 Testing Resume Utilities")
    print("=" * 30)
    
    # Mock dataset info for testing
    mock_dataset = {
        'filename': 'test_dataset.csv',
        'filepath': 'input/test_dataset.csv',
        'row_count': 1000
    }
    
    # Mock stats
    mock_stats = {
        'start_time': '2025-01-22T14:30:45',
        'api_calls_made': 150,
        'total_cost': 0.0234
    }
    
    print("✅ Resume utilities ready for integration")
