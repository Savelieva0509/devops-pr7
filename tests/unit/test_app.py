import os

import pytest

from app import ConfigError, create_app, load_config


# --- відповіді API ---

@pytest.mark.parametrize("path, expected", [
    ("/health", {"status": "ok"}),
    ("/version", {"version": "1.2.3-test"}),
])
def test_routes_return_200_and_json(client, path, expected):
    response = client.get(path)
    assert response.status_code == 200
    assert response.get_json() == expected


def test_unknown_route_returns_404(client):
    assert client.get("/nope").status_code == 404


# --- неправильні налаштування ---

@pytest.mark.parametrize("bad_value", ["", "   "])
def test_empty_version_is_rejected(monkeypatch, bad_value):
    monkeypatch.setenv("APP_VERSION", bad_value)
    with pytest.raises(ConfigError, match="APP_VERSION"):
        create_app()


def test_missing_version_is_rejected(monkeypatch):
    monkeypatch.delenv("APP_VERSION", raising=False)
    with pytest.raises(ConfigError, match="APP_VERSION"):
        create_app()


def test_empty_data_dir_is_rejected(monkeypatch):
    monkeypatch.setenv("APP_VERSION", "1.0")
    monkeypatch.setenv("DATA_DIR", "")
    with pytest.raises(ConfigError, match="DATA_DIR"):
        create_app()


def test_default_data_dir(monkeypatch):
    monkeypatch.setenv("APP_VERSION", "1.0")
    monkeypatch.delenv("DATA_DIR", raising=False)
    assert load_config()["DATA_DIR"] == "/app/data"


# --- /health, коли робоча папка недоступна ---

def test_health_fails_when_data_dir_missing(monkeypatch, tmp_path):
    monkeypatch.setenv("APP_VERSION", "1.0")
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "nope"))
    response = create_app().test_client().get("/health")
    assert response.status_code == 503
    assert response.get_json()["status"] == "error"


def test_health_fails_when_data_dir_read_only(monkeypatch, client):
    monkeypatch.setattr(os, "access", lambda path, mode: False)
    assert client.get("/health").status_code == 503
