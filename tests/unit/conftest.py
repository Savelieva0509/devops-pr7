import pytest

from app import create_app


@pytest.fixture
def client(monkeypatch, tmp_path):
    """Фікстура: застосунок з правильними налаштуваннями + тестовий клієнт."""
    monkeypatch.setenv("APP_VERSION", "1.2.3-test")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    app = create_app()
    app.testing = True
    return app.test_client()
