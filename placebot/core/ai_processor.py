#!/usr/bin/env python3
"""
AI Processor with Anthropic Prompt Caching Implementation
================================================================

"""

import json
import re
import requests
import time
import sys
from typing import Dict, List, Optional, Any


class AIProcessor:
    """Handles AI processing with proper Anthropic prompt caching."""
    
    def __init__(self, model_config: Dict[str, Any]):
        """Initialize AI processor with model configuration."""
        self.model_config = model_config
        self.api_key = model_config.get('api_key', '')
        self.requests_per_minute = model_config.get('requests_per_minute', 50)
        self.last_request_time = 0
        
        # Cache for prompt instructions (loaded once from file)
        self._prompt_cache = None
        
        # Determine caching type based on model
        provider = model_config.get('name', '').lower()
        self.use_claude_caching = 'claude' in provider and 'cached' in provider
        self.use_gemini_caching = 'gemini' in provider and 'cached' in provider
        self.use_caching = self.use_claude_caching or self.use_gemini_caching
        
        # Initialize caching
        self.cached_instructions_message = None  # For Claude
        self.gemini_cached_content_name = None   # For Gemini
        
        cache_type = "Claude" if self.use_claude_caching else "Gemini" if self.use_gemini_caching else "None"
        print(f"AI Processor initialized - Caching: {'SUCCESS ' + cache_type if self.use_caching else 'ERROR Disabled'}")
    
    def _rate_limit(self):
        """Apply rate limiting between API requests."""
        if self.requests_per_minute > 0:
            min_interval = 60 / self.requests_per_minute
            elapsed = time.time() - self.last_request_time
            if elapsed < min_interval:
                time.sleep(min_interval - elapsed)
        self.last_request_time = time.time()
    
    def _get_gemini_cached_content(self):
        """Create and get Gemini cached content (create once, reuse for all calls)."""
        if self.gemini_cached_content_name is None:
            instructions = self._get_full_instructions()
            
            try:
                print("Making Creating Gemini cache...")
                
                # Get model configuration
                model_module = self.model_config.get('module')
                if not model_module or not hasattr(model_module, 'format_cache_request'):
                    print("ERROR Gemini caching not supported for this model configuration")
                    return None
                
                # Create cache request
                cache_request = model_module.format_cache_request(instructions)
                
                # Make cache creation request
                headers = model_module.get_cache_headers(self.api_key)
                cache_endpoint = getattr(model_module, 'CACHE_ENDPOINT', 'https://generativelanguage.googleapis.com/v1beta/cachedContents')
                
                response = requests.post(
                    cache_endpoint,
                    headers=headers,
                    json=cache_request,
                    timeout=60
                )
                
                if response.status_code == 200:
                    cache_data = response.json()
                    self.gemini_cached_content_name = cache_data.get('name', '')
                    
                    print(f"SUCCESS Gemini cache created: {self.gemini_cached_content_name}")
                    
                    # Log cache details
                    usage = cache_data.get('usageMetadata', {})
                    if usage:
                        print(f"   📊 Cached tokens: {usage.get('totalTokenCount', 0)}")
                        
                    expire_time = cache_data.get('expireTime', '')
                    if expire_time:
                        print(f"   ⏰ Expires: {expire_time}")
                        
                else:
                    print(f"ERROR Failed to create Gemini cache: {response.status_code}")
                    print(f"   Error: {response.text}")
                    return None
                    
            except Exception as e:
                print(f"ERROR Gemini cache creation failed: {str(e)}")
                return None
        
        return self.gemini_cached_content_name
    
    def _get_full_instructions(self):
        """Get the full instruction text from external file (cached in memory)."""
        # Return cached version if available
        if self._prompt_cache is not None:
            return self._prompt_cache
        
        # Load prompt from package data using importlib.resources
        # This works in both development and installed package
        try:
            if sys.version_info >= (3, 9):
                # Python 3.9+ - use files() API
                from importlib.resources import files
                prompt_file = files('placebot.data').joinpath('prompt.md')
                self._prompt_cache = prompt_file.read_text(encoding='utf-8')
            else:
                # Python 3.8 - use read_text() API
                from importlib.resources import read_text
                self._prompt_cache = read_text('placebot.data', 'prompt.md')
            
            return self._prompt_cache
            
        except Exception as e:
            raise RuntimeError(
                f"Error loading prompt file from placebot/data/prompt.md: {e}\n"
                f"This file should be included in the package installation."
            )
    
    def _get_cached_instructions(self):
        """Get cached instructions message for Claude (create once, reuse for all calls)."""
        if self.cached_instructions_message is None:
            instructions = self._get_full_instructions()
            
            self.cached_instructions_message = {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": instructions,
                        "cache_control": {"type": "ephemeral"}
                    }
                ]
            }
        
        return self.cached_instructions_message
    
    def _build_prompt(self, locality: str, country: str, coordinate_context: str = "") -> str:
        """Build traditional prompt for non-cached models."""
        instructions = self._get_full_instructions()
        
        return f"""{instructions}

Locality: "{locality}"
Country: {country if country else "[Not provided - please determine from locality text]"}{coordinate_context}

Respond with JSON only."""
    
    def _prepare_coordinate_context(self, locality: str, converted_lat: Optional[float], 
                                  converted_lon: Optional[float], coord_source: str, 
                                  coord_radius: Optional[float] = None) -> str:
        """Prepare coordinate context for the AI prompt."""
        if converted_lat and converted_lon:
            if coord_source == "coordinates_provided":
                return f"\n\nEXISTING COORDINATES: {converted_lat:.6f}, {converted_lon:.6f} (PRESERVE THESE EXACT COORDINATES - do not overwrite)"
            elif coord_source == "grid_reference_converted":
                from .coordinate_utils import detect_grid_references
                detected_grids = detect_grid_references(locality)
                context = f"\n\nGRID REFERENCE CONVERTED: {', '.join(detected_grids)} -> {converted_lat:.6f}, {converted_lon:.6f}"
                if coord_radius:
                    context += f"\nPRECISION RADIUS: {coord_radius:.1f} meters (use this for coordinate_radius_meters field)"
                context += "\nIMPORTANT: PRESERVE these mathematically converted coordinates, do not estimate or overwrite!"
                return context
        
        return "\n\nNO EXISTING COORDINATES: Please estimate coordinates from locality if possible"
    
    def _make_api_request(self, locality: str, country: str, coordinate_context: str = "", max_retries: int = 5) -> Dict[str, Any]:
        """Make API request - cached for Claude, traditional for others."""
        
        for attempt in range(max_retries + 1):
            try:
                self._rate_limit()
                
                if self.use_claude_caching:
                    # CLAUDE CACHED REQUEST
                    print(f"Making Making cached Claude API request (attempt {attempt + 1})")
                    
                    # Build messages array exactly like colleague's example
                    messages = [
                        self._get_cached_instructions(),
                        {
                            "role": "user", 
                            "content": f"Please georeference this locality string: {locality}\nCountry: {country}{coordinate_context}"
                        }
                    ]
                    
                    headers = {
                        'x-api-key': self.api_key,
                        'Content-Type': 'application/json',
                        'anthropic-version': '2023-06-01'
                    }
                    
                    request_body = {
                        'model': self.model_config.get('model_id', 'claude-haiku-4-5'),
                        'max_tokens': self.model_config.get('max_output_tokens', 1000),
                        'messages': messages
                    }
                    
                    endpoint = self.model_config.get('api_endpoint', 'https://api.anthropic.com/v1/messages')
                    
                elif self.use_gemini_caching:
                    # GEMINI CACHED REQUEST
                    print(f"Making Making cached Gemini API request (attempt {attempt + 1})")
                    
                    # Get or create cache
                    cached_content_name = self._get_gemini_cached_content()
                    if not cached_content_name:
                        print("ERROR Failed to get Gemini cache, falling back to traditional request")
                        self.use_gemini_caching = False
                        return self._make_api_request(locality, country, coordinate_context, max_retries)
                    
                    # Get model module for request formatting
                    model_module = self.model_config.get('module')
                    if not model_module:
                        print("ERROR No model module found for Gemini caching")
                        return {'success': False, 'error': 'No model module found'}
                        
                    headers = model_module.get_headers(self.api_key)
                    
                    # Format prompt
                    prompt = f"Please georeference this locality string: {locality}\nCountry: {country}{coordinate_context}"
                    
                    # Use cached content in request
                    request_body = model_module.format_request(
                        prompt, 
                        self.model_config.get('max_output_tokens', 500),
                        cached_content_name
                    )
                    
                    endpoint = self.model_config.get("api_endpoint", "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent")
                    
                else:
                    # TRADITIONAL REQUEST (for non-Claude models)
                    print(f"Making Making traditional API request (attempt {attempt + 1})")
                    
                    model_module = self.model_config.get('module')
                    if model_module and hasattr(model_module, 'get_headers'):
                        headers = model_module.get_headers(self.api_key)
                        prompt = self._build_prompt(locality, country, coordinate_context)
                        request_body = model_module.format_request(prompt, self.model_config.get('max_output_tokens', 500))
                    else:
                        headers = {
                            'x-api-key': self.api_key,
                            'Content-Type': 'application/json',
                            'anthropic-version': '2023-06-01'
                        }
                        prompt = self._build_prompt(locality, country, coordinate_context)
                        request_body = {
                            'model': self.model_config.get('model_id', 'claude-haiku-4-5'),
                            'max_tokens': self.model_config.get('max_output_tokens', 500),
                            'messages': [{'role': 'user', 'content': prompt}]
                        }
                    
                    endpoint = self.model_config.get('api_endpoint', 'https://api.anthropic.com/v1/messages')
                
                # Make the request
                response = requests.post(
                    endpoint,
                    headers=headers,
                    json=request_body,
                    timeout=self.model_config.get('request_timeout', 30)
                )
                
                print(f"API Response: {response.status_code}")
                
                if response.status_code == 200:
                    return {'success': True, 'data': response.json()}
                elif (response.status_code == 429 or response.status_code == 500 or response.status_code == 529) and attempt < max_retries:
                    # Handle rate limits (429), internal errors (500), and overloaded (529) errors
                    if response.status_code == 500:
                        # Internal server error - retry with exponential backoff
                        wait_time = (2 ** attempt) * 4
                        error_type = "Internal server error (500)"
                    elif response.status_code == 529:
                        # Server overloaded - longer wait times
                        wait_time = (2 ** attempt) * 5
                        error_type = "Server overloaded"
                    else:
                        # Rate limit - standard wait
                        wait_time = (2 ** attempt) * 3  
                        error_type = "Rate limit"
                    print(f"Waiting {error_type} hit, waiting {wait_time}s before retry {attempt + 1}/{max_retries}")
                    time.sleep(wait_time)
                    continue
                else:
                    error_details = response.text if hasattr(response, 'text') else 'No details'
                    print(f"ERROR API Error {response.status_code}: {error_details}")
                    return {'success': False, 'error': f'API error: {response.status_code}', 'details': error_details}
                    
            except Exception as e:
                print(f"ERROR Request exception: {str(e)}")
                if attempt < max_retries:
                    print(f"Waiting Retrying {attempt + 1}/{max_retries}")
                    time.sleep(2)
                    continue
                return {'success': False, 'error': f'Request failed: {str(e)}'}
        
        return {'success': False, 'error': 'Max retries exceeded'}
    
    def _extract_token_usage(self, response_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract token usage information from API response (vendor-specific)."""
        token_info = {
            'input_tokens': 0,
            'output_tokens': 0,
            'total_tokens': 0,
            'token_source': 'unknown'
        }
        
        try:
            # Claude format: usage.input_tokens, usage.output_tokens, cache data
            if 'usage' in response_data and 'input_tokens' in response_data['usage']:
                usage = response_data['usage']
                token_info.update({
                    'input_tokens': usage.get('input_tokens', 0),
                    'output_tokens': usage.get('output_tokens', 0),
                    'total_tokens': usage.get('input_tokens', 0) + usage.get('output_tokens', 0),
                    'token_source': 'claude',
                    # Cache-specific token data for Anthropic models
                    'cache_creation_input_tokens': usage.get('cache_creation_input_tokens', 0),
                    'cache_read_input_tokens': usage.get('cache_read_input_tokens', 0)
                })
            
            # OpenAI format: usage.prompt_tokens, usage.completion_tokens, usage.total_tokens + caching
            elif 'usage' in response_data and 'prompt_tokens' in response_data['usage']:
                usage = response_data['usage']
                token_info.update({
                    'input_tokens': usage.get('prompt_tokens', 0),
                    'output_tokens': usage.get('completion_tokens', 0),
                    'total_tokens': usage.get('total_tokens', 0),
                    'token_source': 'openai',
                    # OpenAI Cache Detection - prompt_tokens_details.cached_tokens
                    'cached_tokens': usage.get('prompt_tokens_details', {}).get('cached_tokens', 0)
                })
            
            # Gemini format: usageMetadata.promptTokenCount, usageMetadata.candidatesTokenCount + caching
            elif 'usageMetadata' in response_data:
                usage = response_data['usageMetadata']
                token_info.update({
                    'input_tokens': usage.get('promptTokenCount', 0),
                    'output_tokens': usage.get('candidatesTokenCount', 0),
                    'total_tokens': usage.get('totalTokenCount', 0),
                    'token_source': 'gemini',
                    # Gemini Cache Detection - cachedContentTokenCount for implicit caching
                    'cached_content_token_count': usage.get('cachedContentTokenCount', 0)
                })
                
        except Exception as e:
            # If token extraction fails, just return defaults
            token_info['token_source'] = f'extraction_failed: {str(e)}'
            
        return token_info

    def _extract_valid_json(self, text: str) -> str:
        """Extract valid JSON from text that may contain extra content after the JSON.
        
        This method finds the first complete JSON object and ignores any trailing text.
        Handles cases where models add explanatory text after valid JSON.
        """
        try:
            # Find the start of JSON
            start_idx = text.find('{')
            if start_idx == -1:
                return None
            
            # Count braces to find the end of the JSON object
            brace_count = 0
            for i, char in enumerate(text[start_idx:], start_idx):
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        # Found the end of the JSON object
                        json_text = text[start_idx:i+1]
                        
                        # Test if it's valid JSON by parsing it
                        try:
                            json.loads(json_text)
                            return json_text
                        except json.JSONDecodeError:
                            # If parsing fails, continue looking
                            continue
            
            # If no valid JSON found, return None
            return None
            
        except Exception:
            return None

    def _parse_response(self, response_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse AI response and extract structured data."""
        try:
            # FIRST: Extract token usage from raw response (before model parsing)
            token_usage = self._extract_token_usage(response_data)
            
            # THEN: Use the model's parse_response function if available
            model_module = self.model_config.get('module')
            if model_module and hasattr(model_module, 'parse_response'):
                # Model-specific parsing (handles OpenAI chat format, Gemini format, etc.)
                response_text = model_module.parse_response(response_data)
            else:
                # Fallback for Claude response format
                if 'content' in response_data and response_data['content']:
                    response_text = response_data['content'][0]['text']
                else:
                    response_text = str(response_data)
            
            # Extract JSON from cleaned response text using improved method
            json_text = self._extract_valid_json(response_text)
            if not json_text:
                return {'success': False, 'error': 'No valid JSON found in response'}
            
            parsed_data = json.loads(json_text)
            
            # Validate required fields
            required_fields = ['country', 'state', 'region', 'sector', 'exact_site']
            for field in required_fields:
                if field not in parsed_data:
                    parsed_data[field] = ''
            
            # Type conversion for numeric fields
            for coord_field in ['latitude', 'longitude', 'elevation_meters', 'coordinate_radius_meters']:
                if coord_field in parsed_data and parsed_data[coord_field] is not None:
                    try:
                        parsed_data[coord_field] = float(parsed_data[coord_field])
                    except (ValueError, TypeError):
                        parsed_data[coord_field] = None
            
            # Add token usage information (extracted at start of function)
            parsed_data.update(token_usage)
            
            parsed_data['success'] = True
            return parsed_data
            
        except json.JSONDecodeError as e:
            return {'success': False, 'error': f'JSON parsing failed: {str(e)}'}
        except Exception as e:
            return {'success': False, 'error': f'Response parsing failed: {str(e)}'}
    
    def process_locality(self, locality: str, country: str, existing_lat: Optional[float] = None, 
                        existing_lon: Optional[float] = None, coord_source: str = "", 
                        coord_radius: Optional[float] = None) -> Dict[str, Any]:
        """Process a single locality using AI with caching support."""
        
        print(f"Processing: {locality[:50]}...")
        
        # Prepare coordinate context
        coordinate_context = self._prepare_coordinate_context(locality, existing_lat, existing_lon, coord_source, coord_radius)
        
        # Make API request
        api_response = self._make_api_request(locality, country, coordinate_context)
        
        if not api_response['success']:
            print(f"ERROR API failed: {api_response['error']}")
            return {
                'success': False,
                'error': api_response['error'],
                'country': country,
                'state': '',
                'region': '',
                'sector': '',
                'exact_site': locality,
                'latitude': existing_lat,
                'longitude': existing_lon,
                'coordinate_source': coord_source or 'failed',
                'coordinate_radius_meters': None,
                'elevation_meters': None,
                'elevation_original': '',
                'confidence': 'low',
                'collection_notes': '',
                'notes': f"AI processing failed: {api_response['error']}"
            }
        
        # Parse response
        parsed_result = self._parse_response(api_response['data'])
        
        if not parsed_result['success']:
            print(f"ERROR Parsing failed: {parsed_result['error']}")
            return {
                'success': False,
                'error': parsed_result['error'],
                'country': country,
                'state': '',
                'region': '',
                'sector': '',
                'exact_site': locality,
                'latitude': existing_lat,
                'longitude': existing_lon,
                'coordinate_source': coord_source or 'failed',
                'coordinate_radius_meters': None,
                'elevation_meters': None,
                'elevation_original': '',
                'confidence': 'low',
                'collection_notes': '',
                'notes': f"Response parsing failed: {parsed_result['error']}"
            }
        
        print(f"SUCCESS Success: {parsed_result.get('coordinate_source', 'processed')}")
        
        # Return successful result with token usage data
        return {
            'success': True,
            'country': parsed_result.get('country', country),
            'state': parsed_result.get('state', ''),
            'region': parsed_result.get('region', ''),
            'sector': parsed_result.get('sector', ''),
            'exact_site': parsed_result.get('exact_site', locality),
            'latitude': parsed_result.get('latitude'),
            'longitude': parsed_result.get('longitude'),
            'coordinate_source': parsed_result.get('coordinate_source', ''),
            'coordinate_radius_meters': parsed_result.get('coordinate_radius_meters'),
            'elevation_meters': parsed_result.get('elevation_meters'),
            'elevation_original': parsed_result.get('elevation_original', ''),
            'confidence': parsed_result.get('confidence', 'medium'),
            'collection_notes': parsed_result.get('collection_notes', ''),
            'notes': parsed_result.get('notes', ''),
            # Token usage data (including cache-specific tokens)
            'input_tokens': parsed_result.get('input_tokens', 0),
            'output_tokens': parsed_result.get('output_tokens', 0),
            'total_tokens': parsed_result.get('total_tokens', 0),
            'token_source': parsed_result.get('token_source', 'unknown'),
            'cache_creation_input_tokens': parsed_result.get('cache_creation_input_tokens', 0),
            'cache_read_input_tokens': parsed_result.get('cache_read_input_tokens', 0),
            # OpenAI cache tokens
            'cached_tokens': parsed_result.get('cached_tokens', 0),
            # Gemini cache tokens
            'cached_content_token_count': parsed_result.get('cached_content_token_count', 0)
        }
