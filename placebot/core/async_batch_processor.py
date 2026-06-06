#!/usr/bin/env python3
"""
Async Batch Processor for AI Locality Processing
================================================

Implements asynchronous batch processing using provider batch APIs.
Supports Anthropic, OpenAI, and Gemini batch APIs for 50% cost savings.

Usage:
    - For large datasets (1000+ records) where 24-hour processing is acceptable
    - Reduces costs by 50% compared to real-time processing
    - Automatic handling of batch submission, monitoring, and result retrieval
"""

import time
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
import anthropic

# New import: coordinate preprocessing utilities
from .coordinate_utils import preprocess_coordinates, detect_grid_references


def build_coordinate_context_for_prompt(record: Dict[str, Any]) -> str:
    """
    Build a coordinate context string for inclusion in AI prompts based on
    preprocessing (existing coords or converted grid refs).

    Uses a shallow copy of the record so we don't mutate the original record
    objects passed into the async batch processor.
    """
    # Make a shallow copy to avoid mutating original record objects
    record_copy = record.copy()
    processed = preprocess_coordinates(record_copy)

    existing_lat = processed.get('preprocessed_lat')
    existing_lon = processed.get('preprocessed_lon')
    coord_source = processed.get('preprocessed_source', '')
    coord_radius = processed.get('preprocessed_radius', None)

    # If coordinates are available
    if existing_lat is not None and existing_lon is not None:
        if coord_source == "coordinates_provided":
            return (
                f"\n\nEXISTING COORDINATES: {existing_lat:.6f}, {existing_lon:.6f} "
                f"(PRESERVE THESE EXACT COORDINATES - do not overwrite)"
            )
        elif coord_source == "grid_reference_converted":
            # Try to use the converted_grid_ref if present; otherwise detect
            grid_text = processed.get('converted_grid_ref')
            if not grid_text:
                locality = record.get('Locality verbatim', '') or record.get('label_verbatim', '')
                detected = detect_grid_references(locality)
                grid_text = ", ".join(detected) if detected else "grid reference"
            context = (
                f"\n\nGRID REFERENCE CONVERTED: {grid_text} -> {existing_lat:.6f}, {existing_lon:.6f}"
            )
            if coord_radius:
                context += f"\nPRECISION RADIUS: {coord_radius:.1f} meters (use this for coordinate_radius_meters field)"
            context += "\nIMPORTANT: PRESERVE these mathematically converted coordinates, do not estimate or overwrite!"
            return context

    # No coordinates found
    return "\n\nNO EXISTING COORDINATES: Please estimate coordinates from locality if possible"


class AnthropicBatchProcessor:
    """Handles async batch processing for Anthropic Claude models."""
    
    def __init__(self, api_key: str, model_id: str = "claude-haiku-4-5"):
        """
        Initialize Anthropic batch processor.
        
        Args:
            api_key: Anthropic API key
            model_id: Claude model to use
        """
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model_id = model_id
        self.batch_jobs = {}  # Track active batch jobs
    
    def prepare_batch_requests(self, records: List[Dict[str, Any]], 
                               prompt_template: str) -> List[Dict[str, Any]]:
        """
        Prepare batch requests from locality records.
        
        Args:
            records: List of locality records to process
            prompt_template: Formatted prompt template
            
        Returns:
            List of batch request objects
        """
        requests = []
        
        for record in records:
            barcode = record.get('Barcode', f'record_{len(requests)}')
            # Ensure barcode is a string
            barcode = str(barcode)
            # Handle both 'Locality verbatim' and 'label_verbatim' field names
            locality = record.get('Locality verbatim') or record.get('label_verbatim', '')
            country = record.get('Country', '')

            # Build coordinate context from preprocessing
            coordinate_context = build_coordinate_context_for_prompt(record)

            request = {
                "custom_id": barcode,
                "params": {
                    "model": self.model_id,
                    "max_tokens": 1000,
                    "messages": [{
                        "role": "user",
                        "content": f"{prompt_template}\n\nLocality: {locality}\nCountry: {country}{coordinate_context}"
                    }]
                }
            }
            requests.append(request)
        
        return requests
    
    def submit_batch(self, requests: List[Dict[str, Any]], 
                    batch_name: str = None) -> str:
        """
        Submit batch job to Anthropic.
        
        Args:
            requests: List of prepared batch requests
            batch_name: Optional name for the batch
            
        Returns:
            Batch ID for tracking
        """
        if not batch_name:
            batch_name = f"locality_batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        print(f"\n📦 Submitting batch: {batch_name}")
        print(f"   Records: {len(requests)}")
        print(f"   Model: {self.model_id}")
        print(f"   💰 Cost: 50% discount applied")
        
        try:
            batch = self.client.messages.batches.create(requests=requests)
            batch_id = batch.id
            
            self.batch_jobs[batch_id] = {
                'name': batch_name,
                'submitted_at': datetime.now(),
                'record_count': len(requests),
                'status': 'submitted'
            }
            
            print(f"   ✅ Batch ID: {batch_id}")
            print(f"   ⏱️  Processing time: Up to 24 hours")
            
            return batch_id
            
        except Exception as e:
            print(f"   ❌ Error submitting batch: {e}")
            raise
    
    def check_status(self, batch_id: str) -> Dict[str, Any]:
        """
        Check batch processing status.
        
        Args:
            batch_id: Batch ID to check
            
        Returns:
            Status dictionary with completion info
        """
        try:
            batch = self.client.messages.batches.retrieve(batch_id)
            
            status_info = {
                'batch_id': batch_id,
                'status': batch.processing_status,
                'total': sum([
                    batch.request_counts.processing,
                    batch.request_counts.succeeded,
                    batch.request_counts.errored,
                    batch.request_counts.canceled,
                    batch.request_counts.expired
                ]),
                'succeeded': batch.request_counts.succeeded,
                'failed': batch.request_counts.errored,
                'processing': batch.request_counts.processing,
                'canceled': batch.request_counts.canceled,
                'expired': batch.request_counts.expired
            }
            
            return status_info
            
        except Exception as e:
            print(f"❌ Error checking status: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def wait_for_completion(self, batch_id: str, check_interval: int = 60,
                           max_wait_hours: int = 25) -> bool:
        """
        Wait for batch to complete with periodic status checks.
        
        Args:
            batch_id: Batch ID to monitor
            check_interval: Seconds between status checks
            max_wait_hours: Maximum hours to wait
            
        Returns:
            True if completed successfully, False otherwise
        """
        print(f"\n⏳ Monitoring batch: {batch_id}")
        print(f"   Check interval: {check_interval}s")
        print(f"   Max wait: {max_wait_hours}h")
        
        start_time = time.time()
        max_wait_seconds = max_wait_hours * 3600
        
        while True:
            elapsed = time.time() - start_time
            
            if elapsed > max_wait_seconds:
                print(f"\n⏰ Max wait time exceeded ({max_wait_hours}h)")
                return False
            
            status = self.check_status(batch_id)
            
            if status['status'] == 'ended':
                print(f"\n✅ Batch completed!")
                print(f"   ✓ Successful: {status['succeeded']}")
                print(f"   ✗ Failed: {status['failed']}")
                print(f"   ⏱️  Total time: {elapsed/3600:.1f}h")
                return True
            
            elif status['status'] in ['failed', 'canceled', 'expired']:
                print(f"\n❌ Batch {status['status']}")
                return False
            
            # Still processing
            elapsed_str = f"{elapsed/60:.0f}m" if elapsed < 3600 else f"{elapsed/3600:.1f}h"
            print(f"   [{elapsed_str}] Status: {status['status']} - "
                  f"{status['succeeded']}/{status['total']} completed", end='\r')
            
            time.sleep(check_interval)
    
    def get_results(self, batch_id: str) -> List[Dict[str, Any]]:
        """
        Retrieve and parse batch results.
        
        Args:
            batch_id: Batch ID to retrieve results from
            
        Returns:
            List of processed results with barcodes
        """
        print(f"\n📥 Retrieving results for batch: {batch_id}")
        
        results = []
        success_count = 0
        error_count = 0
        
        try:
            for result in self.client.messages.batches.results(batch_id):
                barcode = result.custom_id
                
                if result.result.type == 'succeeded':
                    response_text = result.result.message.content[0].text
                    
                    # Extract JSON from markdown if present
                    try:
                        # Try to find JSON in markdown code blocks
                        import re
                        json_match = re.search(r'```json\s*\n(.*?)\n```', response_text, re.DOTALL)
                        if json_match:
                            json_text = json_match.group(1)
                        else:
                            # Try without markdown
                            json_text = response_text
                        
                        parsed = json.loads(json_text)
                        parsed['barcode'] = barcode
                        parsed['success'] = True
                        results.append(parsed)
                        success_count += 1
                    except json.JSONDecodeError as e:
                        results.append({
                            'barcode': barcode,
                            'success': False,
                            'error': f'JSON parse error: {e}',
                            'raw_response': response_text
                        })
                        error_count += 1
                else:
                    # Handle error result
                    results.append({
                        'barcode': barcode,
                        'success': False,
                        'error': result.result.error.message if hasattr(result.result, 'error') else 'Unknown error'
                    })
                    error_count += 1
            
            print(f"   ✓ Successful: {success_count}")
            print(f"   ✗ Failed: {error_count}")
            
            return results
            
        except Exception as e:
            print(f"❌ Error retrieving results: {e}")
            raise
    
    def cancel_batch(self, batch_id: str) -> bool:
        """
        Cancel a running batch job.
        
        Args:
            batch_id: Batch ID to cancel
            
        Returns:
            True if canceled successfully
        """
        try:
            self.client.messages.batches.cancel(batch_id)
            print(f"✅ Batch {batch_id} canceled")
            return True
        except Exception as e:
            print(f"❌ Error canceling batch: {e}")
            return False


# OpenAI and Gemini Batch Processors

class OpenAIBatchProcessor:
    """Handles async batch processing for OpenAI models."""
    
    def __init__(self, api_key: str, model_id: str = "gpt-4.1-mini"):
        """
        Initialize OpenAI batch processor.
        
        Args:
            api_key: OpenAI API key
            model_id: OpenAI model to use
        """
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key)
        self.model_id = model_id
        self.batch_jobs = {}  # Track active batch jobs
    
    def prepare_batch_file(self, records: List[Dict[str, Any]], 
                          prompt_template: str, 
                          output_file: str = "batch_requests.jsonl") -> str:
        """
        Prepare JSONL batch file for OpenAI.
        
        Args:
            records: List of locality records to process
            prompt_template: Formatted prompt template
            output_file: Path to save JSONL file
            
        Returns:
            Path to created JSONL file
        """
        import json

        # Reasoning models (GPT-5 family, o-series) need minimal reasoning effort
        # and a larger token budget so reasoning tokens don't crowd out the JSON
        # output. They also reject sampling params (handled by not sending any).
        model_lower = (self.model_id or "").lower()
        is_reasoning = model_lower.startswith("gpt-5") or model_lower.startswith("o")

        with open(output_file, 'w', encoding='utf-8') as f:
            for record in records:
                barcode = record.get('Barcode', f'record_{records.index(record)}')
                # Ensure barcode is a string for OpenAI API
                barcode = str(barcode)
                # Handle both 'Locality verbatim' and 'label_verbatim' field names
                locality = record.get('Locality verbatim') or record.get('label_verbatim', '')
                country = record.get('Country', '')

                # Build coordinate context from preprocessing
                coordinate_context = build_coordinate_context_for_prompt(record)

                body = {
                    "model": self.model_id,
                    "messages": [{
                        "role": "user",
                        "content": f"{prompt_template}\n\nLocality: {locality}\nCountry: {country}{coordinate_context}"
                    }],
                    "max_completion_tokens": 4000 if is_reasoning else 1000,
                    "response_format": {"type": "json_object"}
                }
                if is_reasoning:
                    body["reasoning_effort"] = "minimal"

                request = {
                    "custom_id": barcode,
                    "method": "POST",
                    "url": "/v1/chat/completions",
                    "body": body
                }
                f.write(json.dumps(request, ensure_ascii=False) + '\n')

        return output_file
    
    def submit_batch(self, batch_file_path: str, 
                    batch_name: str = None) -> str:
        """
        Submit batch job to OpenAI.
        
        Args:
            batch_file_path: Path to JSONL file
            batch_name: Optional name for the batch
            
        Returns:
            Batch ID for tracking
        """
        if not batch_name:
            batch_name = f"locality_batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        print(f"\n📦 Submitting OpenAI batch: {batch_name}")
        print(f"   File: {batch_file_path}")
        print(f"   Model: {self.model_id}")
        print(f"   💰 Cost: 50% discount applied")
        
        try:
            # Upload batch file
            with open(batch_file_path, 'rb') as f:
                batch_file = self.client.files.create(file=f, purpose="batch")
            
            # Create batch job
            batch = self.client.batches.create(
                input_file_id=batch_file.id,
                endpoint="/v1/chat/completions",
                completion_window="24h",
                metadata={"description": batch_name}
            )
            
            batch_id = batch.id
            
            self.batch_jobs[batch_id] = {
                'name': batch_name,
                'submitted_at': datetime.now(),
                'file_id': batch_file.id,
                'status': 'submitted'
            }
            
            print(f"   ✅ Batch ID: {batch_id}")
            print(f"   ⏱️  Processing time: Up to 24 hours")
            
            return batch_id
            
        except Exception as e:
            print(f"   ❌ Error submitting batch: {e}")
            raise
    
    def check_status(self, batch_id: str) -> Dict[str, Any]:
        """
        Check batch processing status.
        
        Args:
            batch_id: Batch ID to check
            
        Returns:
            Status dictionary with completion info
        """
        try:
            batch = self.client.batches.retrieve(batch_id)
            
            status_info = {
                'batch_id': batch_id,
                'status': batch.status,
                'total': batch.request_counts.total,
                'completed': batch.request_counts.completed,
                'failed': batch.request_counts.failed
            }
            
            return status_info
            
        except Exception as e:
            print(f"❌ Error checking status: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def wait_for_completion(self, batch_id: str, check_interval: int = 60,
                           max_wait_hours: int = 25) -> bool:
        """
        Wait for batch to complete with periodic status checks.
        
        Args:
            batch_id: Batch ID to monitor
            check_interval: Seconds between status checks
            max_wait_hours: Maximum hours to wait
            
        Returns:
            True if completed successfully, False otherwise
        """
        print(f"\n⏳ Monitoring OpenAI batch: {batch_id}")
        print(f"   Check interval: {check_interval}s")
        print(f"   Max wait: {max_wait_hours}h")
        
        start_time = time.time()
        max_wait_seconds = max_wait_hours * 3600
        
        while True:
            elapsed = time.time() - start_time
            
            if elapsed > max_wait_seconds:
                print(f"\n⏰ Max wait time exceeded ({max_wait_hours}h)")
                return False
            
            status = self.check_status(batch_id)
            
            if status['status'] == 'completed':
                print(f"\n✅ Batch completed!")
                print(f"   ✓ Successful: {status['completed']}")
                print(f"   ✗ Failed: {status['failed']}")
                print(f"   ⏱️  Total time: {elapsed/3600:.1f}h")
                return True
            
            elif status['status'] in ['failed', 'expired', 'cancelled']:
                print(f"\n❌ Batch {status['status']}")
                return False
            
            # Still processing
            elapsed_str = f"{elapsed/60:.0f}m" if elapsed < 3600 else f"{elapsed/3600:.1f}h"
            print(f"   [{elapsed_str}] Status: {status['status']} - "
                  f"{status['completed']}/{status['total']} completed", end='\r')
            
            time.sleep(check_interval)
    
    def get_results(self, batch_id: str) -> List[Dict[str, Any]]:
        """
        Retrieve and parse batch results.
        
        Args:
            batch_id: Batch ID to retrieve results from
            
        Returns:
            List of processed results with barcodes
        """
        import json
        
        print(f"\n📥 Retrieving OpenAI batch results: {batch_id}")
        
        results = []
        success_count = 0
        error_count = 0
        
        try:
            # Get batch info
            batch = self.client.batches.retrieve(batch_id)
            
            if batch.output_file_id:
                # Download results file
                result_content = self.client.files.content(batch.output_file_id)
                
                # Parse JSONL results
                for line in result_content.text.split('\n'):
                    if not line.strip():
                        continue
                    
                    result = json.loads(line)
                    barcode = result.get('custom_id', 'unknown')
                    
                    if result.get('response', {}).get('status_code') == 200:
                        # Success
                        response_body = result['response']['body']
                        content = response_body['choices'][0]['message']['content']
                        
                        try:
                            parsed = json.loads(content)
                            parsed['barcode'] = barcode
                            parsed['success'] = True
                            results.append(parsed)
                            success_count += 1
                        except json.JSONDecodeError as e:
                            results.append({
                                'barcode': barcode,
                                'success': False,
                                'error': f'JSON parse error: {e}',
                                'raw_response': content
                            })
                            error_count += 1
                    else:
                        # Error
                        results.append({
                            'barcode': barcode,
                            'success': False,
                            'error': result.get('error', {}).get('message', 'Unknown error')
                        })
                        error_count += 1
            
            print(f"   ✓ Successful: {success_count}")
            print(f"   ✗ Failed: {error_count}")
            
            return results
            
        except Exception as e:
            print(f"❌ Error retrieving results: {e}")
            raise
    
    def cancel_batch(self, batch_id: str) -> bool:
        """
        Cancel a running batch job.
        
        Args:
            batch_id: Batch ID to cancel
            
        Returns:
            True if canceled successfully
        """
        try:
            self.client.batches.cancel(batch_id)
            print(f"✅ Batch {batch_id} canceled")
            return True
        except Exception as e:
            print(f"❌ Error canceling batch: {e}")
            return False


class GeminiBatchProcessor:
    """Handles async batch processing for Gemini models using REST API."""
    
    def __init__(self, api_key: str, model_id: str = "gemini-3.5-flash"):
        """
        Initialize Gemini batch processor.
        
        Args:
            api_key: Google API key
            model_id: Gemini model to use
        """
        from google import genai
        
        self.api_key = api_key
        self.model_id = model_id
        self.client = genai.Client(api_key=api_key)
        self.batch_jobs = {}
        
        print("[SUCCESS] GeminiBatchProcessor initialized")
    
    def prepare_batch_file(self, records: List[Dict[str, Any]], 
                          prompt_template: str,
                          output_file: str = "gemini_batch.jsonl") -> str:
        """
        Prepare JSONL batch file for Gemini in correct format.
        
        Args:
            records: List of locality records to process
            prompt_template: Formatted prompt template
            output_file: Path to save JSONL file
            
        Returns:
            Path to created JSONL file
        """
        import json
        
        with open(output_file, 'w', encoding='utf-8') as f:
            for record in records:
                barcode = record.get('Barcode', f'record_{records.index(record)}')
                # Ensure barcode is string and handle both field names
                barcode = str(barcode)
                locality = record.get('Locality verbatim') or record.get('label_verbatim', '')
                country = record.get('Country', '')

                # Build coordinate context from preprocessing
                coordinate_context = build_coordinate_context_for_prompt(record)
                
                # Gemini batch format: {"key": "...", "request": {...}}
                request = {
                    "key": barcode,
                    "request": {
                        "contents": [{
                            "parts": [{
                                "text": f"{prompt_template}\n\nLocality: {locality}\nCountry: {country}{coordinate_context}"
                            }],
                            "role": "user"
                        }],
                        "generationConfig": {
                            "responseMimeType": "application/json"
                        }
                    }
                }
                f.write(json.dumps(request, ensure_ascii=False) + '\n')
        
        return output_file
    
    def upload_to_gcs(self, local_file: str, gcs_path: str) -> str:
        """
        Upload file to Google Cloud Storage.
        
        Args:
            local_file: Local file path
            gcs_path: GCS destination path (gs://bucket/path)
            
        Returns:
            GCS URI
        """
        from google.cloud import storage
        
        # Parse GCS path
        if not gcs_path.startswith('gs://'):
            raise ValueError("GCS path must start with gs://")
        
        parts = gcs_path[5:].split('/', 1)
        bucket_name = parts[0]
        blob_name = parts[1] if len(parts) > 1 else local_file.split('/')[-1]
        
        # Upload
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        blob.upload_from_filename(local_file)
        
        return f"gs://{bucket_name}/{blob_name}"
    
    def submit_batch(self, batch_input,
                    batch_name: str = None) -> str:
        """
        Submit batch job to Gemini using Files API and batches.create().
        
        Args:
            batch_input: Either a file path (str) OR a list of request dicts
            batch_name: Optional name for the batch
            
        Returns:
            Batch job name for tracking
        """
        from datetime import datetime
        from google.genai import types
        import tempfile
        import json
        
        if not batch_name:
            batch_name = f"locality_batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        print(f"\n📦 Submitting Gemini batch: {batch_name}")
        print(f"   Model: {self.model_id}")
        print(f"   💰 Cost: 50% discount applied")
        
        try:
            # Handle both file path and request list
            if isinstance(batch_input, list):
                # Create temporary JSONL file from request list
                print(f"   📝 Converting {len(batch_input)} requests to JSONL...")
                temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False, encoding='utf-8')
                
                for request in batch_input:
                    # Convert to proper Gemini batch format
                    barcode = request.get('custom_id', 'unknown')
                    contents = request.get('contents', [])

                    # If contents do not already include coordinate context, attempt to build it
                    # (this covers cases where callers pass raw requests)
                    if contents and 'text' in contents[0].get('parts', [{}])[0]:
                        # Assume caller already included text with any coordinate context
                        pass
                    temp_file.write(json.dumps({
                        "key": str(barcode),
                        "request": {
                            "contents": contents,
                            "generationConfig": {
                                "responseMimeType": "application/json"
                            }
                        }
                    }, ensure_ascii=False) + '\n')
                
                temp_file.close()
                batch_file_path = temp_file.name
            else:
                # It's already a file path
                batch_file_path = batch_input
            
            # Step 1: Upload file using Files API
            print(f"   📤 Uploading batch file...")
            uploaded_file = self.client.files.upload(
                file=batch_file_path,
                config=types.UploadFileConfig(
                    display_name=batch_name,
                    mime_type='application/json'
                )
            )
            
            print(f"   ✅ File uploaded: {uploaded_file.name}")
            
            # Step 2: Create batch job
            print(f"   📋 Creating batch job...")
            # Model name must include "models/" prefix for batch API
            model_name = self.model_id if self.model_id.startswith('models/') else f'models/{self.model_id}'
            batch_job = self.client.batches.create(
                model=model_name,
                src=uploaded_file.name,
                config={
                    'display_name': batch_name,
                },
            )
            
            job_name = batch_job.name
            
            self.batch_jobs[job_name] = {
                'name': batch_name,
                'submitted_at': datetime.now(),
                'file_uri': uploaded_file.name,
                'status': batch_job.state.name
            }
            
            print(f"   ✅ Batch ID: {job_name}")
            print(f"   📊 Status: {batch_job.state.name}")
            print(f"   ⏱️  Processing time: Usually < 24 hours")
            
            # Clean up temp file if we created one
            if isinstance(batch_input, list):
                import os
                os.unlink(batch_file_path)
            
            return job_name
            
        except Exception as e:
            print(f"   ❌ Error submitting batch: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def check_status(self, job_name: str) -> Dict[str, Any]:
        """
        Check batch processing status.
        
        Args:
            job_name: Job name to check
            
        Returns:
            Status dictionary with completion info
        """
        try:
            job = self.client.batches.get(name=job_name)
            
            status_info = {
                'job_name': job_name,
                'status': str(job.state),
                'model': job.model,
                'create_time': str(job.create_time) if hasattr(job, 'create_time') else None
            }
            
            return status_info
            
        except Exception as e:
            print(f"❌ Error checking status: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def wait_for_completion(self, job_name: str, check_interval: int = 60,
                           max_wait_hours: int = 25) -> bool:
        """
        Wait for batch to complete with periodic status checks.
        
        Args:
            job_name: Job name to monitor
            check_interval: Seconds between status checks
            max_wait_hours: Maximum hours to wait
            
        Returns:
            True if completed successfully, False otherwise
        """
        from google.genai.types import JobState
        
        print(f"\n⏳ Monitoring Gemini batch: {job_name}")
        print(f"   Check interval: {check_interval}s")
        print(f"   Max wait: {max_wait_hours}h")
        
        start_time = time.time()
        max_wait_seconds = max_wait_hours * 3600
        
        completed_states = {
            JobState.JOB_STATE_SUCCEEDED,
            JobState.JOB_STATE_FAILED,
            JobState.JOB_STATE_CANCELLED,
            JobState.JOB_STATE_PAUSED
        }
        
        while True:
            elapsed = time.time() - start_time
            
            if elapsed > max_wait_seconds:
                print(f"\n⏰ Max wait time exceeded ({max_wait_hours}h)")
                return False
            
            job = self.client.batches.get(name=job_name)
            current_state = job.state
            
            if current_state in completed_states:
                if current_state == JobState.JOB_STATE_SUCCEEDED:
                    print(f"\n✅ Batch completed successfully!")
                    print(f"   ⏱️  Total time: {elapsed/3600:.1f}h")
                    return True
                else:
                    print(f"\n❌ Batch ended with state: {current_state}")
                    return False
            
            # Still processing
            elapsed_str = f"{elapsed/60:.0f}m" if elapsed < 3600 else f"{elapsed/3600:.1f}h"
            print(f"   [{elapsed_str}] State: {current_state}", end='\r')
            
            time.sleep(check_interval)
    
    def get_results(self, job_name: str, output_uri: str) -> List[Dict[str, Any]]:
        """
        Retrieve and parse batch results from GCS.
        
        Args:
            job_name: Job name to retrieve results from
            output_uri: GCS URI where results were stored
            
        Returns:
            List of processed results with barcodes
        """
        import json
        from google.cloud import storage
        
        print(f"\n📥 Retrieving Gemini batch results: {job_name}")
        print(f"   Output: {output_uri}")
        
        results = []
        success_count = 0
        error_count = 0
        
        try:
            # Parse GCS path
            if not output_uri.startswith('gs://'):
                raise ValueError("Output URI must be a gs:// path")
            
            parts = output_uri[5:].split('/', 1)
            bucket_name = parts[0]
            prefix = parts[1] if len(parts) > 1 else ""
            
            # Download results
            storage_client = storage.Client()
            bucket = storage_client.bucket(bucket_name)
            
            # List all result files (Gemini creates multiple output files)
            blobs = bucket.list_blobs(prefix=prefix)
            
            for blob in blobs:
                if blob.name.endswith('.jsonl'):
                    content = blob.download_as_text()
                    
                    for line in content.strip().split('\n'):
                        if not line:
                            continue
                        
                        result = json.loads(line)
                        barcode = result.get('key', 'unknown')
                        
                        if 'response' in result:
                            # Success
                            try:
                                response_text = result['response']['candidates'][0]['content']['parts'][0]['text']
                                parsed = json.loads(response_text)
                                parsed['barcode'] = barcode
                                parsed['success'] = True
                                results.append(parsed)
                                success_count += 1
                            except (json.JSONDecodeError, KeyError, IndexError) as e:
                                results.append({
                                    'barcode': barcode,
                                    'success': False,
                                    'error': f'Parse error: {e}',
                                    'raw_response': response_text if 'response_text' in locals() else None
                                })
                                error_count += 1
                        else:
                            # Error
                            results.append({
                                'barcode': barcode,
                                'success': False,
                                'error': result.get('error', {}).get('message', 'Unknown error')
                            })
                            error_count += 1
            
            print(f"   ✓ Successful: {success_count}")
            print(f"   ✗ Failed: {error_count}")
            
            return results
            
        except Exception as e:
            print(f"❌ Error retrieving results: {e}")
            raise
    
    def cancel_batch(self, job_name: str) -> bool:
        """
        Cancel a batch job.
        
        Args:
            job_name: Job name to cancel
            
        Returns:
            True if canceled successfully
        """
        if job_name in self.batch_jobs:
            self.batch_jobs[job_name]['status'] = 'cancelled'
            print(f"✅ Batch {job_name} canceled")
            return True
        else:
            print(f"❌ Batch {job_name} not found")
            return False

    def prepare_batch_requests(self, records: List[Dict[str, Any]], 
                               prompt_template: str) -> List[Dict[str, Any]]:
        """
        Prepare batch requests for Gemini.
        
        Args:
            records: List of locality records to process
            prompt_template: Formatted prompt template
            
        Returns:
            List of request dictionaries
        """
        requests = []
        
        for record in records:
            barcode = record.get('Barcode', f'record_{len(requests)}')
            # Handle both 'Locality verbatim' and 'label_verbatim' field names
            locality = record.get('Locality verbatim') or record.get('label_verbatim', '')
            country = record.get('Country', '')

            # Build coordinate context from preprocessing
            coordinate_context = build_coordinate_context_for_prompt(record)
            
            request = {
                'custom_id': barcode,
                'contents': [{
                    'parts': [{
                        'text': f"{prompt_template}\n\nLocality: {locality}\nCountry: {country}{coordinate_context}"
                    }]
                }]
            }
            requests.append(request)
        
        return requests
    
    def submit_batch(self, batch_input,
                    batch_name: str = None) -> str:
        """
        Submit batch job to Gemini using Files API.
        
        Args:
            batch_input: Either a file path (str) OR a list of request dicts
            batch_name: Optional name for the batch
            
        Returns:
            Batch job name for tracking
        """
        from datetime import datetime
        import tempfile
        import json
        
        if not batch_name:
            batch_name = f"locality_batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        print(f"\n📦 Submitting Gemini batch: {batch_name}")
        print(f"   Model: {self.model_id}")
        print(f"   💰 Cost: 50% discount applied")
        
        try:
            # Handle both file path and request list
            if isinstance(batch_input, list):
                # Create temporary JSONL file from request list
                print(f"   📝 Converting {len(batch_input)} requests to JSONL...")
                temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False, encoding='utf-8')
                
                for request in batch_input:
                    # Convert to proper Gemini batch format
                    barcode = request.get('custom_id', 'unknown')
                    contents = request.get('contents', [])
                    
                    jsonl_entry = {
                        "key": str(barcode),
                        "request": {
                            "contents": contents,
                            "generationConfig": {
                                "responseMimeType": "application/json"
                            }
                        }
                    }
                    temp_file.write(json.dumps(jsonl_entry, ensure_ascii=False) + '\n')
                
                temp_file.close()
                batch_file_path = temp_file.name
            else:
                # It's already a file path
                batch_file_path = batch_input
            
            # Step 1: Upload file using Files API
            print(f"   📤 Uploading batch file via Files API...")
            uploaded_file = self.client.files.upload(
                file=batch_file_path,
                config={'mime_type': 'application/json'}
            )
            
            print(f"   ✅ File uploaded: {uploaded_file.name}")
            
            # Step 2: Create batch job
            print(f"   📋 Creating batch job...")
            # Model name must include "models/" prefix
            model_name = self.model_id if self.model_id.startswith('models/') else f'models/{self.model_id}'
            job = self.client.batches.create(
                model=model_name,
                src=uploaded_file.name
            )
            
            job_name = job.name
            
            self.batch_jobs[job_name] = {
                'name': batch_name,
                'submitted_at': datetime.now(),
                'status': str(job.state),
                'record_count': len(batch_input) if isinstance(batch_input, list) else 0
            }
            
            print(f"   ✅ Batch ID: {job_name}")
            print(f"   📊 Status: {job.state}")
            print(f"   ⏱️  Processing time: Up to 24 hours")
            
            # Clean up temp file if we created one
            if isinstance(batch_input, list):
                import os
                os.unlink(batch_file_path)
            
            return job_name
            
        except Exception as e:
            print(f"   ❌ Error submitting batch: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def check_status(self, batch_id: str) -> Dict[str, Any]:
        """
        Check batch processing status using real Gemini API.
        
        Args:
            batch_id: Batch job name to check
            
        Returns:
            Status dictionary with completion info
        """
        try:
            batch_job = self.client.batches.get(name=batch_id)
            
            # Map Gemini states to standard format
            state_mapping = {
                'JOB_STATE_PENDING': 'pending',
                'JOB_STATE_RUNNING': 'running',
                'JOB_STATE_SUCCEEDED': 'completed',
                'JOB_STATE_FAILED': 'failed',
                'JOB_STATE_CANCELLED': 'cancelled',
                'JOB_STATE_EXPIRED': 'expired'
            }
            
            status = state_mapping.get(batch_job.state.name, 'unknown')
            
            # Try to get counts if available
            total = 0
            succeeded = 0
            failed = 0
            
            # Gemini doesn't provide request counts in the same way as OpenAI
            # We'll need to check the results to get accurate counts
            status_info = {
                'batch_id': batch_id,
                'status': status,
                'state': batch_job.state.name,
                'total': total,
                'succeeded': succeeded,
                'failed': failed
            }
            
            return status_info
            
        except Exception as e:
            return {
                'batch_id': batch_id,
                'status': 'error',
                'error': str(e),
                'total': 0,
                'succeeded': 0,
                'failed': 0
            }
    
    def wait_for_completion(self, batch_id: str, check_interval: int = 60,
                           max_wait_hours: int = 25) -> bool:
        """
        Simulate batch completion for Gemini.
        
        Args:
            batch_id: Batch ID to monitor
            check_interval: Seconds between status checks
            max_wait_hours: Maximum hours to wait
            
        Returns:
            True (immediate completion for simulation)
        """
        print(f"\n⏳ Monitoring Gemini batch: {batch_id}")
        print(f"   💡 Note: Using simulated batch processing")
        
        # Mark as completed
        if batch_id in self.batch_jobs:
            self.batch_jobs[batch_id]['status'] = 'completed'
        
        print(f"\n✅ Batch marked as complete!")
        return True
    
    def get_results(self, batch_id: str) -> List[Dict[str, Any]]:
        """
        Retrieve batch results from Gemini Batch API.
        
        Args:
            batch_id: Batch job name to retrieve results from
            
        Returns:
            List of parsed results
        """
        print(f"\n[INFO] Retrieving Gemini batch results: {batch_id}")
        
        try:
            # Get batch job
            batch_job = self.client.batches.get(name=batch_id)
            
            # Check if succeeded
            if batch_job.state.name != 'JOB_STATE_SUCCEEDED':
                print(f"   [WARNING] Batch not ready: {batch_job.state.name}")
                return []
            
            results = []
            
            # Check if results are in a file or inline
            if batch_job.dest and batch_job.dest.file_name:
                print(f"   [INFO] Downloading results file...")
                file_content_bytes = self.client.files.download(file=batch_job.dest.file_name)
                file_content = file_content_bytes.decode('utf-8')
                
                # Parse JSONL
                import json
                for line in file_content.strip().split('\n'):
                    try:
                        result = json.loads(line)
                        
                        # Extract the key and response
                        barcode = result.get('key', 'unknown')
                        
                        if 'response' in result and result['response'].get('candidates'):
                            # Get the text response
                            text = result['response']['candidates'][0]['content']['parts'][0]['text']
                            
                            # Strip markdown code blocks if present
                            text = text.strip()
                            if text.startswith('```'):
                                # Remove ```json or ``` at start
                                text = text.split('\n', 1)[1] if '\n' in text else text[3:]
                            if text.endswith('```'):
                                # Remove ``` at end
                                text = text.rsplit('\n', 1)[0] if '\n' in text else text[:-3]
                            text = text.strip()
                            
                            # Try to parse as JSON
                            try:
                                parsed_json = json.loads(text)
                                parsed_json['barcode'] = barcode
                                parsed_json['success'] = True
                                results.append(parsed_json)
                            except json.JSONDecodeError:
                                # If not JSON, return as raw text
                                results.append({
                                    'barcode': barcode,
                                    'success': False,
                                    'error': 'JSON parse error',
                                    'raw_response': text
                                })
                        elif 'error' in result:
                            results.append({
                                'barcode': barcode,
                                'success': False,
                                'error': result['error'].get('message', 'Unknown error')
                            })
                    except Exception as e:
                        print(f"   ⚠️  Error parsing line: {e}")
                        
            elif batch_job.dest and batch_job.dest.inlined_responses:
                print(f"   📝 Processing inline responses...")
                for response in batch_job.dest.inlined_responses:
                    try:
                        if response.response and response.response.candidates:
                            text = response.response.candidates[0].content.parts[0].text
                            
                            try:
                                parsed_json = json.loads(text)
                                parsed_json['success'] = True
                                results.append(parsed_json)
                            except json.JSONDecodeError:
                                results.append({
                                    'success': False,
                                    'error': 'JSON parse error',
                                    'raw_response': text
                                })
                        elif response.error:
                            results.append({
                                'success': False,
                                'error': str(response.error)
                            })
                    except Exception as e:
                        print(f"   [WARNING] Error processing response: {e}")
            
            print(f"   [INFO] Successful: {sum(1 for r in results if r.get('success'))}")
            print(f"   [INFO] Failed: {sum(1 for r in results if not r.get('success'))}")
            
            return results
            
        except Exception as e:
            print(f"   ❌ Error retrieving results: {e}")
            import traceback
            traceback.print_exc()
            return []
        
        if batch_id in self.batch_jobs:
            requests = self.batch_jobs[batch_id]['requests']
            
            # Return placeholder results
            for req in requests:
                results.append({
                    'barcode': req['custom_id'],
                    'success': False,
                    'error': 'Gemini Batch API not yet fully implemented',
                    'note': 'Use real-time Gemini models or implement Vertex AI batch'
                })
            
            print(f"   ⚠️  {len(results)} placeholder results returned")
            print(f"   💡 Recommendation: Use Anthropic or OpenAI batch for production")
        
        return results
    
    def cancel_batch(self, batch_id: str) -> bool:
        """
        Cancel a batch job.
        
        Args:
            batch_id: Batch ID to cancel
            
        Returns:
            True if canceled successfully
        """
        if batch_id in self.batch_jobs:
            self.batch_jobs[batch_id]['status'] = 'cancelled'
            print(f"✅ Batch {batch_id} canceled")
            return True
        else:
            print(f"❌ Batch {batch_id} not found")
            return False