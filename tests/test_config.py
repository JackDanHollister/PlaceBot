"""Tests for API key configuration and persistence."""

from placebot.core.config import Config, get_user_env_path


def test_save_and_get_api_key_roundtrip(isolated_home):
    cfg = Config()
    cfg.save_api_key("google", "AIzaTESTKEY1234567890")

    env_path = get_user_env_path()
    assert env_path.exists()
    # A freshly constructed Config should pick the key up from ~/.placebot/.env
    assert Config().get_api_key("google") == "AIzaTESTKEY1234567890"


def test_gemini_alias_maps_to_google(isolated_home):
    cfg = Config()
    cfg.save_api_key("gemini", "AIzaABCDEFGHIJKLMNOP")
    assert Config().get_api_key("google") == "AIzaABCDEFGHIJKLMNOP"


def test_clearing_key_removes_it(isolated_home):
    cfg = Config()
    cfg.save_api_key("openai", "sk-proj-1234567890")
    assert cfg.get_api_key("openai") == "sk-proj-1234567890"

    cfg.save_api_key("openai", "")
    assert Config().get_api_key("openai") is None


def test_check_api_keys_reports_status(isolated_home):
    cfg = Config()
    cfg.save_api_key("anthropic", "sk-ant-XXXXXXXXXXXX")
    status = Config().check_api_keys()
    assert status["anthropic"] is True
    assert status["openai"] is False


def test_save_key_only_replaces_target_provider(isolated_home):
    cfg = Config()
    cfg.save_api_key("anthropic", "sk-ant-AAAAAAAAAAAA")
    cfg.save_api_key("google", "AIzaBBBBBBBBBBBB")
    reloaded = Config()
    assert reloaded.get_api_key("anthropic") == "sk-ant-AAAAAAAAAAAA"
    assert reloaded.get_api_key("google") == "AIzaBBBBBBBBBBBB"
