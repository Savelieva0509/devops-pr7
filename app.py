"""Невеликий сервіс для Практичної 7: маршрути /health і /version."""
import os

from flask import Flask, jsonify


class ConfigError(RuntimeError):
    """Неправильні налаштування у змінних середовища."""


def load_config(environ=None):
    """Читає налаштування зі змінних середовища і перевіряє їх."""
    env = os.environ if environ is None else environ
    version = env.get("APP_VERSION", "").strip()
    if not version:
        raise ConfigError("APP_VERSION не задано: сервіс не знає своєї версії")
    data_dir = env.get("DATA_DIR", "/app/data").strip()
    if not data_dir:
        raise ConfigError("DATA_DIR порожній")
    return {"APP_VERSION": version, "DATA_DIR": data_dir}


def create_app(environ=None):
    """Створює застосунок Flask (gunicorn викликає цю функцію)."""
    config = load_config(environ)
    app = Flask(__name__)
    app.config.update(config)

    @app.get("/health")
    def health():
        data_dir = app.config["DATA_DIR"]
        if os.path.isdir(data_dir) and os.access(data_dir, os.W_OK):
            return jsonify(status="ok"), 200
        return jsonify(status="error",
                       reason=f"немає доступу на запис до {data_dir}"), 503

    @app.get("/version")
    def version():
        return jsonify(version=app.config["APP_VERSION"]), 200

    return app
