#!/usr/bin/env python3
"""
Model Selection Utility for BGE Locality Processor
=================================================

Handles loading and selecting AI models from profile files.
Each model has its own configuration file with API keys, pricing, and capabilities.
"""

import os
import importlib.util
from typing import Dict, List, Optional, Any
import sys

def discover_models() -> List[str]:
    """Discover available model profile files in the models/ directory."""
    # Get the directory containing this script, then go up one level to find models/
    current_dir = os.path.dirname(os.path.abspath(__file__))
    models_dir = os.path.join(os.path.dirname(current_dir), "models")
    
    if not os.path.exists(models_dir):
        return []
    
    model_files = []
    for filename in os.listdir(models_dir):
        if filename.endswith('.py') and not filename.startswith('__'):
            model_name = filename[:-3]  # Remove .py extension
            model_files.append(model_name)
    
    return sorted(model_files)


def load_model_profile(model_file: str) -> Optional[Dict[str, Any]]:
    """Load a model profile from a .py file."""
    try:
        # Get the directory containing this script, then go up one level to find models/
        current_dir = os.path.dirname(os.path.abspath(__file__))
        models_dir = os.path.join(os.path.dirname(current_dir), "models")
        file_path = os.path.join(models_dir, f"{model_file}.py")
        
        if not os.path.exists(file_path):
            return None
        
        # Load the module dynamically
        spec = importlib.util.spec_from_file_location(model_file, file_path)
        if spec is None or spec.loader is None:
            return None
            
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Extract model information
        profile = {
            'name': getattr(module, 'MODEL_NAME', model_file),
            'provider': getattr(module, 'MODEL_PROVIDER', 'Unknown'),
            'model_id': getattr(module, 'MODEL_ID', ''),
            'api_endpoint': getattr(module, 'API_ENDPOINT', ''),
            'api_key': getattr(module, 'API_KEY', ''),
            'cost_per_1k_input': getattr(module, 'COST_PER_1K_INPUT_TOKENS', 0),
            'cost_per_1k_output': getattr(module, 'COST_PER_1K_OUTPUT_TOKENS', 0),
            'estimated_cost_per_record': getattr(module, 'ESTIMATED_COST_PER_RECORD', 0),
            'max_tokens': getattr(module, 'MAX_TOKENS', 4096),
            'max_output_tokens': getattr(module, 'MAX_OUTPUT_TOKENS', 2000),
            'requests_per_minute': getattr(module, 'REQUESTS_PER_MINUTE', 50),
            'speed': getattr(module, 'SPEED', 'Unknown'),
            'accuracy': getattr(module, 'ACCURACY', 'Unknown'),
            'cost_efficiency': getattr(module, 'COST_EFFICIENCY', 'Unknown'),
            'best_for': getattr(module, 'BEST_FOR', ''),
            'get_headers': getattr(module, 'get_headers', None),
            'format_request': getattr(module, 'format_request', None),
            'parse_response': getattr(module, 'parse_response', None),
            'module': module  # Keep reference to the module
        }
        
        return profile
        
    except Exception as e:
        print(f"Error loading model profile {model_file}: {e}")
        return None


def display_model_selection(models: List[Dict[str, Any]]) -> None:
    """Display available models in a nice table format."""
    
    print("\n" + "=" * 80)
    print("🤖 AVAILABLE AI MODELS FOR LOCALITY PROCESSING")
    print("=" * 80)
    
    if not models:
        print("❌ No model profiles found in models/ directory")
        print("Please add model profile files to get started.")
        return
    
    for i, model in enumerate(models, 1):
        print(f"\n[{i}] {model['name']} ({model['provider']})")
        print(f"    💰 Cost per record: ${model['estimated_cost_per_record']:.4f}")
        print(f"    ⚡ Speed: {model['speed']} | 🎯 Accuracy: {model['accuracy']} | 💡 Cost Efficiency: {model['cost_efficiency']}")
        print(f"    📊 Rate limit: {model['requests_per_minute']} req/min | 🔤 Max tokens: {model['max_output_tokens']:,}")
        print(f"    🎯 Best for: {model['best_for']}")
        
        # Check if API key is configured
        if model['api_key'] and len(model['api_key']) > 10:
            print(f"    🔑 API Key: Configured ({model['api_key'][:15]}...)")
        else:
            print(f"    ⚠️  API Key: Not configured")
    
    print("\n" + "=" * 80)


def select_model_interactive() -> Optional[Dict[str, Any]]:
    """Interactive model selection with user input."""
    
    # Discover available models
    model_files = discover_models()
    
    if not model_files:
        print("❌ No model profiles found!")
        print("Create model profile files in the models/ directory first.")
        return None
    
    # Load model profiles
    models = []
    for model_file in model_files:
        profile = load_model_profile(model_file)
        if profile:
            models.append(profile)
    
    if not models:
        print("❌ No valid model profiles could be loaded!")
        return None
    
    # Display models
    display_model_selection(models)
    
    # Get user selection
    while True:
        try:
            print(f"\nSelect a model (1-{len(models)}) or 'q' to quit: ", end="")
            choice = input().strip().lower()
            
            if choice == 'q':
                print("Model selection cancelled.")
                return None
            
            model_index = int(choice) - 1
            
            if 0 <= model_index < len(models):
                selected_model = models[model_index]
                
                # Validate API key
                if not selected_model['api_key'] or len(selected_model['api_key']) < 10:
                    print(f"\n⚠️  Warning: {selected_model['name']} has no API key configured!")
                    print(f"Edit models/{model_files[model_index]}.py to add your API key.")
                    continue_anyway = input("Continue anyway? (y/n): ").strip().lower()
                    if continue_anyway != 'y':
                        continue
                
                print(f"\n✅ Selected: {selected_model['name']}")
                print(f"💰 Estimated cost per record: ${selected_model['estimated_cost_per_record']:.4f}")
                return selected_model
            else:
                print(f"Please enter a number between 1 and {len(models)}")
                
        except ValueError:
            print("Please enter a valid number or 'q' to quit")
        except KeyboardInterrupt:
            print("\nModel selection cancelled.")
            return None


def calculate_batch_cost(model: Dict[str, Any], num_records: int, batch_size: int) -> Dict[str, float]:
    """Calculate estimated costs for batch processing."""
    
    num_batches = (num_records + batch_size - 1) // batch_size  # Round up
    
    # Rough estimates based on typical prompt sizes
    avg_input_tokens_per_batch = 1600 + (batch_size * 100)  # Base prompt + record data
    avg_output_tokens_per_batch = batch_size * 130  # Estimated output per record
    
    total_input_tokens = num_batches * avg_input_tokens_per_batch
    total_output_tokens = num_batches * avg_output_tokens_per_batch
    
    input_cost = (total_input_tokens / 1000) * model['cost_per_1k_input']
    output_cost = (total_output_tokens / 1000) * model['cost_per_1k_output']
    total_cost = input_cost + output_cost
    
    estimated_time_minutes = num_batches * (60 / model['requests_per_minute'])
    
    return {
        'total_cost': total_cost,
        'input_cost': input_cost,
        'output_cost': output_cost,
        'num_batches': num_batches,
        'estimated_time_minutes': estimated_time_minutes,
        'cost_per_record': total_cost / num_records if num_records > 0 else 0
    }


def get_model_by_name(model_name: str) -> Optional[Dict[str, Any]]:
    """Get a specific model by its file name."""
    return load_model_profile(model_name)


if __name__ == "__main__":
    # Test the model selection system
    print("🧪 Testing Model Selection System")
    selected = select_model_interactive()
    
    if selected:
        print(f"\nTest successful! Selected model: {selected['name']}")
        
        # Test cost calculation
        costs = calculate_batch_cost(selected, 100, 8)
        print(f"Cost for 100 records: ${costs['total_cost']:.4f}")
        print(f"Estimated time: {costs['estimated_time_minutes']:.1f} minutes")
    else:
        print("No model selected.")
