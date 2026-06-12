"""
Gemini Batch Processor - Real Implementation
=============================================

Uses Google's actual Batch API with genai.Client().batches.create()
"""

import json
import time
from datetime import datetime
from typing import Dict, List, Any

def create_gemini_batch_processor():
    """Create Gemini batch processor using real Batch API."""
    
    class GeminiBatchProcessor:
        """Gemini batch processing using google-genai SDK Batch API."""
        
        def __init__(self, api_key: str, model_id: str = "gemini-3.5-flash"):
            """Initialize with API key and model ID."""
            import google.genai as genai
            
            self.client = genai.Client(api_key=api_key)
            self.genai = genai
            self.api_key = api_key
            self.model_id = model_id
            self.batch_jobs = {}
            print("✅ GeminiBatchProcessor ready")
        
        def prepare_batch_requests(self, records: List[Dict[str, Any]], 
                                   prompt_template: str) -> List[Dict[str, Any]]:
            """Prepare inline batch requests list for Gemini."""
            requests_list = []
            
            from .field_mapping import get_ai_locality, get_country, get_identifier

            for idx, record in enumerate(records):
                barcode = get_identifier(record, default=f'record_{idx}')
                locality = get_ai_locality(record)
                country = get_country(record)
                
                # Format as Gemini batch request
                request = {
                    'contents': [{
                        'parts': [{
                            'text': f"{prompt_template}\n\nLocality: {locality}\nCountry: {country}"
                        }],
                        'role': 'user'
                    }],
                    'config': {
                        'temperature': 0.1,
                        'max_output_tokens': 1000
                    }
                }
                requests_list.append(request)
            
            return requests_list
        
        def submit_batch(self, requests_list: List[Dict], batch_name: str = None) -> str:
            """
            Submit batch job using Gemini Batch API.
            
            Uses inline requests (under 20MB) for simplicity.
            """
            if not batch_name:
                batch_name = f"gemini_batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            print(f"\n📦 Submitting Gemini batch: {batch_name}")
            print(f"   Records: {len(requests_list)}")
            print(f"   Model: {self.model_id}")
            
            try:
                # Create batch job with inline requests
                print(f"   📋 Creating batch job...")
                batch_job = self.client.batches.create(
                    model=f"models/{self.model_id}",
                    src=requests_list  # Changed from 'requests' to 'src'
                )
                
                batch_id = batch_job.name
                self.batch_jobs[batch_id] = {
                    'name': batch_name,
                    'created_at': datetime.now().isoformat()
                }
                
                print(f"   ✅ Batch ID: {batch_id}")
                print(f"   💰 Cost: 50% discount applied")
                print(f"   ⏱️  Processing time: Up to 24 hours")
                
                return batch_id
                
            except Exception as e:
                print(f"   ❌ Error: {e}")
                raise
        
        def check_status(self, batch_id: str) -> Dict[str, Any]:
            """Check batch job status."""
            try:
                batch = self.client.batches.get(name=batch_id)  # Fixed: use name= keyword
                
                # Map Gemini state to our standard format
                state = batch.state.name.lower() if hasattr(batch, 'state') else 'unknown'
                
                total = 0
                succeeded = 0
                failed = 0
                
                if hasattr(batch, 'request_counts'):
                    total = batch.request_counts.total if hasattr(batch.request_counts, 'total') else 0
                    succeeded = batch.request_counts.succeeded if hasattr(batch.request_counts, 'succeeded') else 0
                    failed = batch.request_counts.failed if hasattr(batch.request_counts, 'failed') else 0
                
                return {
                    'batch_id': batch_id,
                    'status': state,
                    'total': total,
                    'succeeded': succeeded,
                    'failed': failed
                }
            except Exception as e:
                return {
                    'batch_id': batch_id,
                    'status': 'error', 
                    'error': str(e),
                    'total': 0,
                    'succeeded': 0,
                    'failed': 0
                }
        
        def get_results(self, batch_id: str) -> List[Dict[str, Any]]:
            """Download and parse batch results."""
            print(f"\n📥 Retrieving results for batch: {batch_id}")
            
            try:
                batch = self.client.batches.get(name=batch_id)  # Fixed: use name= keyword
                
                state = batch.state.name if hasattr(batch, 'state') else 'UNKNOWN'
                if state != 'JOB_STATE_SUCCEEDED':  # Fixed: check for full state name
                    print(f"   ⚠️  Batch not ready: {state}")
                    return []
                
                # Get results from batch
                print(f"   📊 Parsing results...")
                results = []
                success_count = 0
                error_count = 0
                
                # Iterate through batch responses
                for idx, response in enumerate(batch.responses):
                    try:
                        if hasattr(response, 'response') and response.response.candidates:
                            text = response.response.candidates[0].content.parts[0].text
                            
                            # Extract JSON from markdown
                            import re
                            json_match = re.search(r'```json\s*\n(.*?)\n```', text, re.DOTALL)
                            if json_match:
                                json_text = json_match.group(1)
                            else:
                                json_text = text
                            
                            try:
                                parsed = json.loads(json_text)
                                parsed['barcode'] = f'record_{idx}'  # Add barcode
                                parsed['success'] = True
                                results.append(parsed)
                                success_count += 1
                            except json.JSONDecodeError as e:
                                results.append({
                                    'barcode': f'record_{idx}',
                                    'success': False,
                                    'error': f'JSON parse error: {e}',
                                    'raw_response': text
                                })
                                error_count += 1
                        else:
                            results.append({
                                'barcode': f'record_{idx}',
                                'success': False,
                                'error': 'No response from model'
                            })
                            error_count += 1
                    except Exception as e:
                        results.append({
                            'barcode': f'record_{idx}',
                            'success': False,
                            'error': str(e)
                        })
                        error_count += 1
                
                print(f"   ✓ Successful: {success_count}")
                print(f"   ✗ Failed: {error_count}")
                
                return results
                
            except Exception as e:
                print(f"   ❌ Error: {e}")
                raise
    
    return GeminiBatchProcessor
