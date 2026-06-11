"""Tests for API key configuration and persistence."""

import os
import stat

from placebot.core.config import Config, get_user_env_path


def test_save_and_get_api_key_roundtrip(isolated_home):
    cfg = Config()
    cfg.save_api_key("google", "AIzaTESTKEY1234567890")

    env_path = get_user_env_path()
    assert env_path.exists()
    # A freshly constructed Config should pick the key up from ~/.placebot/.env
    assert Config().get_api_key("google") == "AIzaTESTKEY1234567890"


def test_saved_api_key_file_is_owner_only(isolated_home):
    cfg = Config()
    cfg.save_api_key("openai", "sk-proj-1234567890")

    mode = stat.S_IMODE(os.stat(get_user_env_path()).st_mode)
    assert mode == 0o600


def test_gemini_alias_maps_to_google(isolated_home):
    cfg = Config()
    cfg.save_api_key("gemini", "AIzaABCDEFGHIJKLMNOP")
    assert Config().get_api_key("google") == "AIzaABCDEFGHIJKLMNOP"


def test_openrouter_key_roundtrip(isolated_home):
    cfg = Config()
    cfg.save_api_key("openrouter", "sk-or-v1-1234567890")

    reloaded = Config()
    assert reloaded.get_api_key("openrouter") == "sk-or-v1-1234567890"
    assert reloaded.check_api_keys()["openrouter"] is True


def test_clearing_key_removes_it(isolated_home):
    cfg = Config()
    cfg.save_api_key("openai", "sk-proj-1234567890")
    assert cfg.get_api_key("openai") == "sk-proj-1234567890"

    cfg.save_api_key("openai", "")
    assert Config().get_api_key("openai") is None


def test_check_api_keys_reports_status(isolated_home, monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    cfg = Config()
    cfg.save_api_key("anthropic", "sk-ant-XXXXXXXXXXXX")
    status = Config().check_api_keys()
    assert status["anthropic"] is True
    assert status["openai"] is False
    assert status["openrouter"] is False


def test_save_key_only_replaces_target_provider(isolated_home):
    cfg = Config()
    cfg.save_api_key("anthropic", "sk-ant-AAAAAAAAAAAA")
    cfg.save_api_key("google", "AIzaBBBBBBBBBBBB")
    reloaded = Config()
    assert reloaded.get_api_key("anthropic") == "sk-ant-AAAAAAAAAAAA"
    assert reloaded.get_api_key("google") == "AIzaBBBBBBBBBBBB"


def test_save_multiple_google_keys(isolated_home):
    cfg = Config()
    cfg.save_google_api_keys(["AIzaPRIMARY1234567890", "AIzaSECOND1234567890"])

    reloaded = Config()
    # Primary maps to GOOGLE_API_KEY for backward compatibility
    assert reloaded.get_api_key("google") == "AIzaPRIMARY1234567890"
    assert reloaded.get_google_api_keys() == [
        "AIzaPRIMARY1234567890",
        "AIzaSECOND1234567890",
    ]


def test_save_google_keys_skips_blanks(isolated_home):
    cfg = Config()
    cfg.save_google_api_keys(["AIzaPRIMARY1234567890", "", "  "])
    assert Config().get_google_api_keys() == ["AIzaPRIMARY1234567890"]


def test_save_fewer_google_keys_clears_extra_slots(isolated_home):
    cfg = Config()
    cfg.save_google_api_keys(["AIzaPRIMARY1234567890", "AIzaSECOND1234567890"])
    assert len(Config().get_google_api_keys()) == 2

    # Saving a shorter list should drop the now-unused second slot
    cfg.save_google_api_keys(["AIzaPRIMARY1234567890"])
    assert Config().get_google_api_keys() == ["AIzaPRIMARY1234567890"]


def test_clearing_google_keys_does_not_disturb_other_providers(isolated_home):
    cfg = Config()
    cfg.save_api_key("openai", "sk-proj-1234567890")
    cfg.save_google_api_keys(["AIzaPRIMARY1234567890", "AIzaSECOND1234567890"])

    cfg.save_google_api_keys([])
    reloaded = Config()
    assert reloaded.get_google_api_keys() == []
    assert reloaded.get_api_key("openai") == "sk-proj-1234567890"
