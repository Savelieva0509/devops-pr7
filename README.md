# Практична 7 — автоматизоване тестування та розгортання Python-сервісу

Невеликий Flask-сервіс із двома маршрутами та DevOps-процес навколо нього:
перевірка коду → збірка образу → розгортання на навчальну VM → перевірка → автоматичний відкат.

| Маршрут | Відповідь |
|---|---|
| `GET /health` | `200 {"status":"ok"}` — сервіс готовий; `503` — немає доступу на запис до `DATA_DIR` |
| `GET /version` | `{"version": "<APP_VERSION>"}` — у CI це хеш коміту |

## Структура

| Файл | Призначення |
|---|---|
| `app.py` | застосунок; налаштування лише зі змінних середовища (`APP_VERSION` обов'язкова) |
| `requirements.txt`, `requirements-dev.txt` | зафіксовані версії залежностей (застосунок / тести) |
| `Dockerfile` | образ на `python:3.14.10-slim@sha256:…`, користувач `app` без root, HEALTHCHECK |
| `compose.yaml`, `.env.example` | опис запуску; налаштування через змінні середовища |
| `tests/unit/` | pytest: фікстура, параметризація, monkeypatch |
| `tests/infra/` | Testinfra для запущеного контейнера |
| `scripts/deploy.sh` | розгортання з перевірками і автоматичним відкатом |
| `.github/workflows/ci-cd.yml` | CI/CD у GitHub Actions |

## Запуск локально

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
docker build --build-arg APP_VERSION=local-test -t devops7-app:local .
cp .env.example .env
docker compose up -d --wait --wait-timeout 60
curl --max-time 5 http://127.0.0.1:8000/health
curl --max-time 5 http://127.0.0.1:8000/version
```

## Перевірка

```bash
pytest -v                                         # 10 unit-тестів
pytest tests/infra -v --hosts=docker://devops7-app # 7 тестів Testinfra
scripts/deploy.sh local                           # повний цикл: запуск + /health + Testinfra
```

## Розгортання і відкат

`scripts/deploy.sh <тег>` запускає образ із заданим тегом, чекає `healthy` (до 60 с),
перевіряє `/health` (тайм-аут 5 с) і Testinfra. Тег робочої версії зберігається
в `~/.devops7/current_tag`. Якщо перевірки не пройшли — скрипт зберігає логи,
повертає попередній образ, перевіряє його ще раз і завершується з кодом 1.

Ручний відкат на конкретну версію (на VM):

```bash
cat ~/.devops7/current_tag                         # яка версія зараз робоча
export IMAGE_NAME=ghcr.io/savelieva0509/devops-pr7
docker pull $IMAGE_NAME:<хеш_коміту>
source .venv/bin/activate
scripts/deploy.sh <хеш_коміту>
```

Або через Git: `git revert` проблемного коміту → PR → після злиття CI/CD розгорне виправлену версію.

## CI/CD (GitHub Actions)

| Робота | Де | Коли |
|---|---|---|
| Тести pytest | `ubuntu-latest` | кожен PR і кожне злиття в `main`; звіт `pytest-report` завжди |
| Збірка образу | `ubuntu-latest` | після тестів; тег = хеш коміту; після злиття — push у `ghcr.io/savelieva0509/devops-pr7` |
| Розгортання на VM | self-hosted runner `devops7` на навчальній VM | тільки після злиття; `deploy.sh`; артефакт `deploy-reports` (звіти Testinfra + логи контейнера) завжди |

Правило `protect-main`: у `main` лише через PR, перевірки «Тести pytest» і «Збірка образу» обов'язкові.

## Експерименти зі збоями

1. **Зламаний тест** (PR #2): «Тести pytest» ❌, збірка і розгортання пропущені, злиття заблоковане правилом. На VM лишилася попередня версія.
2. **Несправний `/health`** (PR #3, Dockerfile без `chown /app/data`): тести і збірка ✅, після злиття контейнер `unhealthy` → автоматичний відкат на `6126ef2…` → повторна перевірка ✅ → робота «Розгортання на VM» ❌ (запуск #5).

## Розміщення: VM, IaaS чи PaaS

Зараз сервіс працює на навчальній Linux-VM (VirtualBox), а GitHub керує нею через self-hosted runner.
Для переносу на IaaS (VM в AWS EC2, Azure, Hetzner Cloud) достатньо створити Linux-VM, встановити Docker, Compose і runner — workflow не зміниться, але оновлення ОС, Docker і runner'а, мережевий захист і резервні копії залишаються на нас.
На PaaS (наприклад, Google Cloud Run, Azure App Service для контейнерів, Render) VM і runner не потрібні: workflow передає платформі образ із GHCR, а перевірку здоров'я, перемикання версій і оновлення середовища бере на себе провайдер — ми відповідаємо лише за образ і налаштування.
Витрати створюють сама VM або екземпляри PaaS (час роботи, CPU/RAM), диски та знімки, вихідний трафік, сховище образів понад безкоштовний ліміт і хвилини GitHub Actions для приватних репозиторіїв.
