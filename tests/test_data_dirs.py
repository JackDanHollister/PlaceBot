"""Tests for user data directory resolution and creation."""

from pathlib import Path

from placebot.core import data_dirs


def test_placebot_home_uses_env_override(monkeypatch, tmp_path):
    monkeypatch.setenv("PLACEBOT_HOME", str(tmp_path / "custom"))
    assert data_dirs.get_placebot_home() == tmp_path / "custom"


def test_default_home_is_under_user_home(monkeypatch, tmp_path):
    monkeypatch.delenv("PLACEBOT_HOME", raising=False)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    assert data_dirs.get_placebot_home() == tmp_path / ".placebot"


def test_setup_directories_creates_tree(monkeypatch, tmp_path):
    monkeypatch.setenv("PLACEBOT_HOME", str(tmp_path / "pb"))
    dirs = data_dirs.setup_directories()
    assert Path(dirs["input"]).is_dir()
    assert Path(dirs["output"]).is_dir()
    assert Path(dirs["batch_jobs"]).is_dir()
