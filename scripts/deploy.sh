#!/usr/bin/env bash
# Розгортання образу з перевірками і автоматичним відкатом.
# Використання: scripts/deploy.sh <тег_образу>   (тег = хеш коміту)
set -uo pipefail

NEW_TAG="${1:?Вкажіть тег образу}"
export IMAGE_NAME="${IMAGE_NAME:-devops7-app}"
export CONTAINER_NAME="${CONTAINER_NAME:-devops7-app}"
export APP_PORT="${APP_PORT:-8000}"
WAIT_TIMEOUT="${WAIT_TIMEOUT:-60}"   # скільки чекати готовності, с
HTTP_TIMEOUT="${HTTP_TIMEOUT:-5}"    # тайм-аут одного HTTP-запиту, с
REPORTS="${REPORTS:-reports}"
STATE_FILE="${STATE_FILE:-$HOME/.devops7/current_tag}"  # тег, що працює зараз

mkdir -p "$REPORTS" "$(dirname "$STATE_FILE")"
PREV_TAG="$(cat "$STATE_FILE" 2>/dev/null || true)"

start() {   # запустити образ з тегом $1 і дочекатися healthy
  IMAGE_TAG="$1" docker compose up -d --wait --wait-timeout "$WAIT_TIMEOUT"
}

check() {   # HTTP /health + Testinfra; $1 - назва для звіту
  curl --fail --silent --show-error --max-time "$HTTP_TIMEOUT" \
       "http://127.0.0.1:${APP_PORT}/health" && echo &&
  pytest tests/infra -q --hosts="docker://${CONTAINER_NAME}" \
         --junitxml="${REPORTS}/testinfra-$1.xml"
}

version() {
  curl -s --max-time "$HTTP_TIMEOUT" "http://127.0.0.1:${APP_PORT}/version"
}

echo "== Розгортання ${IMAGE_NAME}:${NEW_TAG} (зараз працює: ${PREV_TAG:-нічого})"
if start "$NEW_TAG" && check deploy; then
  echo "$NEW_TAG" > "$STATE_FILE"
  echo "== УСПІХ: працює $(version)"
  exit 0
fi

echo "== ПОМИЛКА: версія $NEW_TAG не пройшла перевірки"
docker logs "$CONTAINER_NAME" > "${REPORTS}/container-failed.log" 2>&1 || true

if [ -z "$PREV_TAG" ]; then
  echo "== Відкат неможливий: немає попередньої робочої версії"
  exit 1
fi

echo "== ВІДКАТ на попередню версію $PREV_TAG"
if start "$PREV_TAG" && check rollback; then
  echo "== Відкат успішний: працює $(version)"
else
  echo "== ВІДКАТ НЕ ВДАВСЯ - потрібне ручне втручання"
fi
exit 1   # невдале розгортання завжди лишається помилкою
