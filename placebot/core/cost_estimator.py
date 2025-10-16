#!/usr/bin/env python3
"""
Cost Estimation for Locality Processor
======================================

Calculates estimated costs for processing datasets with different models.
"""

from typing import Dict, Any, List


class CostEstimator:
    """Estimates processing costs for different models and modes."""
    
    @staticmethod
    def estimate_tokens_per_record(locality_text: str = None) -> int:
        """
        Estimate tokens needed per record.
        
        Args:
            locality_text: Sample locality text (optional)
            
        Returns:
            Estimated tokens per record
        """
        # Base instruction prompt: ~2000 tokens (cached)
        # Average locality text: ~100 tokens
        # Response: ~100 tokens
        # Total per request: ~200 tokens (most is cached)
        
        if locality_text:
            # Rough approximation: 1 token ≈ 4 characters
            text_tokens = len(locality_text) // 4
        else:
            text_tokens = 100  # Average
        
        return text_tokens + 100  # text + response
    
    @staticmethod
    def estimate_cost(
        num_records: int,
        model_config: Dict[str, Any],
        processing_mode: str = 'realtime',
        with_caching: bool = True
    ) -> Dict[str, Any]:
        """
        Estimate processing cost for a dataset.
        
        Args:
            num_records: Number of records to process
            model_config: Model configuration with pricing info
            processing_mode: 'realtime' or 'batch'
            with_caching: Whether caching is enabled
            
        Returns:
            Dictionary with cost breakdown
        """
        # Get pricing from model config
        input_price = model_config.get('input_cost_per_million', 0)
        output_price = model_config.get('output_cost_per_million', 0)
        
        # Estimate tokens
        tokens_per_record = CostEstimator.estimate_tokens_per_record()
        total_input_tokens = tokens_per_record * num_records
        total_output_tokens = 100 * num_records  # ~100 tokens per response
        
        # Calculate base cost
        base_input_cost = (total_input_tokens / 1_000_000) * input_price
        base_output_cost = (total_output_tokens / 1_000_000) * output_price
        base_total = base_input_cost + base_output_cost
        
        # Apply caching discount
        if with_caching:
            # Instruction prompt is ~2000 tokens and cached
            # Only the locality text + response are uncached (~200 tokens)
            # Caching saves ~90% on input tokens
            cache_savings = base_input_cost * 0.90
            final_input_cost = base_input_cost - cache_savings
        else:
            cache_savings = 0
            final_input_cost = base_input_cost
        
        # Apply batch mode discount (50% off)
        if processing_mode == 'batch':
            batch_discount = (final_input_cost + base_output_cost) * 0.50
            final_total = (final_input_cost + base_output_cost) - batch_discount
        else:
            batch_discount = 0
            final_total = final_input_cost + base_output_cost
        
        return {
            'num_records': num_records,
            'processing_mode': processing_mode,
            'with_caching': with_caching,
            'base_cost': base_total,
            'cache_savings': cache_savings,
            'batch_discount': batch_discount,
            'estimated_cost': final_total,
            'cost_per_record': final_total / num_records if num_records > 0 else 0,
            'total_savings': cache_savings + batch_discount,
            'savings_percentage': ((cache_savings + batch_discount) / base_total * 100) if base_total > 0 else 0
        }
    
    @staticmethod
    def compare_models(
        num_records: int,
        model_configs: List[Dict[str, Any]],
        processing_mode: str = 'realtime'
    ) -> List[Dict[str, Any]]:
        """
        Compare costs across multiple models.
        
        Args:
            num_records: Number of records to process
            model_configs: List of model configurations
            processing_mode: 'realtime' or 'batch'
            
        Returns:
            List of cost estimates sorted by price
        """
        comparisons = []
        
        for config in model_configs:
            model_name = config.get('name', 'Unknown')
            has_caching = 'cached' in model_name.lower()
            
            estimate = CostEstimator.estimate_cost(
                num_records,
                config,
                processing_mode,
                with_caching=has_caching
            )
            
            estimate['model_name'] = model_name
            estimate['model_type'] = config.get('type', 'unknown')
            comparisons.append(estimate)
        
        # Sort by estimated cost
        comparisons.sort(key=lambda x: x['estimated_cost'])
        
        return comparisons
