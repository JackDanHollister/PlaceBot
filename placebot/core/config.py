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


def get_user_env_path() -> Path:
    """Return the path to the user-level .env file (``~/.placebot/.env``)."""
    return Path.home() / ".placebot" / ".env"


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
            self.config_dir = Path(__file__).parent.parent.parent / "config"

        self.config_dir.mkdir(exist_ok=True)
        self._load_env_file()

    def _load_env_file(self):
        """
        Load environment variables from .env files.

        Search order (later files override earlier ones):
          1. <config_dir>/.env          (project config dir)
          2. <project_root>/.env        (repo checkout)
          3. ~/.placebot/.env           (user home - used by the GUI)

        The user home file is loaded last with ``override=True`` so that keys
        entered through the GUI take precedence over any stale project-level
        ``.env`` left behind in a checkout.
        """
        # 1. Project config directory
        env_file = self.config_dir / ".env"
        if env_file.exists():
            load_dotenv(env_file)

        # 2. Project root (editable/source checkout)
        root_env = Path(__file__).parent.parent.parent / ".env"
        if root_env.exists():
            load_dotenv(root_env)

        # 3. User home directory (authoritative - written by the GUI)
        home_env = get_user_env_path()
        if home_env.exists():
            load_dotenv(home_env, override=True)

    # Maximum number of Gemini/Google keys supported (primary + extras).
    # Mirrors the GOOGLE_API_KEY, GOOGLE_API_KEY_2 ... convention documented
    # for large-batch processing.
    MAX_GOOGLE_KEYS = 4

    def get_api_key(self, provider: str) -> Optional[str]:
        """
        Get API key for a specific provider.

        Args:
            provider: Provider name (anthropic, openai, google)

        Returns:
            API key string or None if not found
        """
        key_map = {
            "anthropic": "ANTHROPIC_API_KEY",
            "openai": "OPENAI_API_KEY",
            "google": "GOOGLE_API_KEY",
            "gemini": "GOOGLE_API_KEY",
            "openrouter": "OPENROUTER_API_KEY",
        }

        env_var = key_map.get(provider.lower())
        if not env_var:
            return None

        return os.getenv(env_var)

    def get_google_api_keys(self) -> list:
        """
        Return all configured Google/Gemini API keys in priority order.

        The primary key lives in ``GOOGLE_API_KEY`` and optional additional
        keys (used to spread very large jobs across quotas) live in
        ``GOOGLE_API_KEY_2`` ... ``GOOGLE_API_KEY_N``.
        """
        keys = []
        primary = os.getenv("GOOGLE_API_KEY")
        if primary:
            keys.append(primary)
        for i in range(2, self.MAX_GOOGLE_KEYS + 1):
            value = os.getenv(f"GOOGLE_API_KEY_{i}")
            if value:
                keys.append(value)
        return keys

    def get_all_api_keys(self) -> Dict[str, Optional[str]]:
        """
        Get all API keys.

        Returns:
            Dictionary of provider names to API keys
        """
        return {
            "anthropic": self.get_api_key("anthropic"),
            "openai": self.get_api_key("openai"),
            "google": self.get_api_key("google"),
            "openrouter": self.get_api_key("openrouter"),
        }

    def check_api_keys(self) -> Dict[str, bool]:
        """
        Check which API keys are configured.

        Returns:
            Dictionary of provider names to availability status
        """
        keys = self.get_all_api_keys()
        return {provider: bool(key) for provider, key in keys.items()}

    def save_api_key(self, provider: str, api_key: str) -> Path:
        """
        Persist an API key to ``~/.placebot/.env`` and load it into the
        current process.

        Used primarily by the GUI so non-technical users can paste a key once
        and have it remembered across sessions.

        Args:
            provider: Provider name (anthropic, openai, google/gemini)
            api_key: The API key value to store (an empty string removes it)

        Returns:
            Path to the .env file that was written
        """
        key_map = {
            "anthropic": "ANTHROPIC_API_KEY",
            "openai": "OPENAI_API_KEY",
            "google": "GOOGLE_API_KEY",
            "gemini": "GOOGLE_API_KEY",
            "openrouter": "OPENROUTER_API_KEY",
        }
        env_var = key_map.get(provider.lower())
        if not env_var:
            raise ValueError(f"Unknown provider: {provider}")

        return self._set_env_vars({env_var: api_key})

    def save_google_api_keys(self, api_keys: list) -> Path:
        """
        Persist one or more Google/Gemini API keys.

        The first key is stored as ``GOOGLE_API_KEY`` and any additional keys
        as ``GOOGLE_API_KEY_2`` ... ``GOOGLE_API_KEY_N``. Empty entries are
        skipped, and any previously stored slot beyond the supplied list is
        cleared so the GUI can remove keys.

        Args:
            api_keys: Ordered list of key strings (blank entries are ignored)

        Returns:
            Path to the .env file that was written
        """
        # Drop blank entries but keep order; primary first.
        cleaned = [k.strip() for k in api_keys if k and k.strip()]

        updates: Dict[str, str] = {}
        for slot in range(1, self.MAX_GOOGLE_KEYS + 1):
            env_var = "GOOGLE_API_KEY" if slot == 1 else f"GOOGLE_API_KEY_{slot}"
            # Empty string removes the slot from the .env file.
            updates[env_var] = cleaned[slot - 1] if slot - 1 < len(cleaned) else ""

        return self._set_env_vars(updates)

    def _set_env_vars(self, updates: Dict[str, str]) -> Path:
        """
        Write a batch of ``KEY=value`` pairs to ``~/.placebot/.env``.

        An empty value removes the corresponding line. Existing unrelated
        lines are preserved. New values are also pushed into ``os.environ`` so
        they take effect immediately within the running process.

        Args:
            updates: Mapping of environment variable name to value

        Returns:
            Path to the .env file that was written
        """
        env_path = get_user_env_path()
        env_path.parent.mkdir(parents=True, exist_ok=True)

        remaining = dict(updates)
        lines = []
        if env_path.exists():
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    stripped = line.strip()
                    matched = None
                    for env_var in remaining:
                        if stripped.startswith(f"{env_var}=") or stripped.startswith(
                            f"{env_var} ="
                        ):
                            matched = env_var
                            break
                    if matched is not None:
                        value = remaining.pop(matched)
                        if value:
                            lines.append(f"{matched}={value}\n")
                        # else: drop the line entirely (key removed)
                    else:
                        lines.append(line)

        # Append any keys that weren't already present in the file
        for env_var, value in remaining.items():
            if value:
                if lines and not lines[-1].endswith("\n"):
                    lines.append("\n")
                lines.append(f"{env_var}={value}\n")

        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(lines)
        try:
            os.chmod(env_path, 0o600)
        except OSError:
            pass

        # Make the new values visible to the running process immediately
        for env_var, value in updates.items():
            if value:
                os.environ[env_var] = value
            else:
                os.environ.pop(env_var, None)
        load_dotenv(env_path, override=True)

        return env_path

    def create_env_template(self):
        """Create a .env template file with placeholder API keys."""
        template_path = self.config_dir / ".env.template"

        template_content = """# PlaceBot API Keys
# ============================
# Copy this file to .env and add your actual API keys


# Anthropic (Claude models)
ANTHROPIC_API_KEY=sk-ant-your-key-here

# OpenAI (GPT models)  
OPENAI_API_KEY=sk-your-key-here

# Google (Gemini models)
GOOGLE_API_KEY=your-key-here

# OpenRouter (many vendors through one key)
OPENROUTER_API_KEY=sk-or-your-key-here

# Note: Local Ollama models don't require API keys
"""

        with open(template_path, "w") as f:
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
