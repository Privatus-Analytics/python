import pytest

from privatus_analytics import Config


def test_site_id_is_none_by_default():
    assert Config().resolved_site_id() is None


def test_site_id_falls_back_to_the_environment_variable(monkeypatch):
    monkeypatch.setenv("PRIVATUS_SITE_ID", "pa_FROMENV123")
    assert Config().resolved_site_id() == "pa_FROMENV123"


def test_an_explicit_site_id_wins_over_the_environment_variable(monkeypatch):
    monkeypatch.setenv("PRIVATUS_SITE_ID", "pa_FROMENV123")
    assert Config(site_id=" pa_EXPLICIT01 ").resolved_site_id() == "pa_EXPLICIT01"


def test_script_host_defaults_and_drops_a_trailing_slash(monkeypatch):
    assert Config().resolved_script_host() == "https://privatusstats.com"
    assert Config(script_host="https://stats.example.com/").resolved_script_host() == "https://stats.example.com"
    monkeypatch.setenv("PRIVATUS_SCRIPT_HOST", "https://env.example.com/")
    assert Config().resolved_script_host() == "https://env.example.com"


def test_only_production_is_enabled_by_default(monkeypatch):
    assert Config(environment="production").is_enabled()
    assert not Config(environment="development").is_enabled()
    assert not Config().is_enabled()
    monkeypatch.setenv("PRIVATUS_ENV", "production")
    assert Config().is_enabled()


def test_enabled_forces_the_tag_on_or_off():
    assert Config(enabled=True, environment="development").is_enabled()
    assert not Config(enabled=False, environment="production").is_enabled()


def test_from_mapping_rejects_unknown_settings():
    assert Config.from_mapping({"site_id": "pa_X"}).site_id == "pa_X"
    with pytest.raises(TypeError, match="sit_id"):
        Config.from_mapping({"sit_id": "pa_X"})
