#!/usr/bin/env python3
"""
Configuration Management for Locality Processor
===============================================

Handles API keys, model configurations, and user settings.
"""

import os
from pathlib import Path
from typing import Dict, Optional
from dotenv import load_dotenv


class Config:
    """Manages configuration and API keys for the locality processor."""
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize configuration.
        
        Args:
            config_dir: Optional custom config directory path
        """
        if config_dir:
            self.config_dir = Path(config_dir)
        else:
            # Use project root config directory
            self.config_dir = Path(__file__).parent.parent.parent / 'config'
        
        self.config_dir.mkdir(exist_ok=True)
        self._load_env_file()
    
    def _load_env_file(self):
        """Load environment variables from .env file if it exists."""
        env_file = self.config_dir / '.env'
        
        if env_file.exists():
            load_dotenv(env_file)
        else:
            # Also try loading from project root
            root_env = Path(__file__).parent.parent.parent / '.env'
            if root_env.exists():
                load_dotenv(root_env)
    
    def get_api_key(self, provider: str) -> Optional[str]:
        """
        Get API key for a specific provider.
        
        Args:
            provider: Provider name (anthropic, openai, google)
            
        Returns:
            API key string or None if not found
        """
        key_map = {
            'anthropic': 'ANTHROPIC_API_KEY',
            'openai': 'OPENAI_API_KEY',
            'google': 'GOOGLE_API_KEY',
            'gemini': 'GOOGLE_API_KEY',
        }
        
        env_var = key_map.get(provider.lower())
        if not env_var:
            return None
        
        return os.getenv(env_var)
    
    def get_all_api_keys(self) -> Dict[str, Optional[str]]:
        """
        Get all API keys.
        
        Returns:
            Dictionary of provider names to API keys
        """
        return {
            'anthropic': self.get_api_key('anthropic'),
            'openai': self.get_api_key('openai'),
            'google': self.get_api_key('google'),
        }
    
    def check_api_keys(self) -> Dict[str, bool]:
        """
        Check which API keys are configured.
        
        Returns:
            Dictionary of provider names to availability status
        """
        keys = self.get_all_api_keys()
        return {provider: bool(key) for provider, key in keys.items()}
    
    def create_env_template(self):
        """Create a .env template file with placeholder API keys."""
        template_path = self.config_dir / '.env.template'
        
        template_content = """# Locality Processor API Keys
# ============================
# Copy this file to .env and add your actual API keys


# Anthropic (Claude models)
ANTHROPIC_API_KEY=sk-ant-your-key-here

# OpenAI (GPT models)  
OPENAI_API_KEY=sk-your-key-here

# Google (Gemini models)
GOOGLE_API_KEY=your-key-here

# Note: Local Ollama models don't require API keys
"""
        
        with open(template_path, 'w') as f:
            f.write(template_content)
        
        return template_path


# Singleton instance
_config_instance = None

def get_config() -> Config:
    """Get the global configuration instance."""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance
