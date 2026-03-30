#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/linktranscriber-api}"
SERVICE_NAME="${SERVICE_NAME:-linktranscriber-api}"
PORT="${PORT:-18001}"
PYTHON_BIN="${PYTHON_BIN:-/opt/miniconda3/bin/python}"
SYSTEMD_TEMPLATE="${APP_DIR}/deploy/systemd/linktranscriber-api.service.template"
SYSTEMD_TARGET="/etc/systemd/system/${SERVICE_NAME}.service"

if [[ ! -x "${PYTHON_BIN}" ]]; then
  echo "Python not found: ${PYTHON_BIN}" >&2
  exit 1
fi

cd "${APP_DIR}"

mkdir -p config data note_results static uploads logs

if [[ ! -d .venv ]]; then
  "${PYTHON_BIN}" -m venv .venv
fi

.venv/bin/python -m pip install --upgrade pip setuptools wheel
.venv/bin/pip install -r backend/requirements-service.txt

if [[ ! -f .env.production ]]; then
  cp .env.example .env.production
fi

python3 - <<'PY'
from pathlib import Path
env_path = Path(".env.production")
content = env_path.read_text(encoding="utf-8")
required = {
    "BACKEND_PORT": "18001",
    "BACKEND_HOST": "127.0.0.1",
    "ENV": "production",
    "STATIC": "/static",
    "OUT_DIR": "./static/screenshots",
    "NOTE_OUTPUT_DIR": "note_results",
    "IMAGE_BASE_URL": "/static/screenshots",
    "DATA_DIR": "data",
    "TRANSCRIBER_TYPE": "bcut",
    "WHISPER_MODEL_SIZE": "base",
}
lines = content.splitlines()
keys = {line.split("=", 1)[0].strip() for line in lines if "=" in line}
for key, value in required.items():
    if key not in keys:
        lines.append(f"{key}={value}")
env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
PY

sed \
  -e "s#__APP_DIR__#${APP_DIR}#g" \
  -e "s#__PORT__#${PORT}#g" \
  "${SYSTEMD_TEMPLATE}" > "${SYSTEMD_TARGET}"

systemctl daemon-reload
systemctl enable "${SERVICE_NAME}"
systemctl restart "${SERVICE_NAME}"

for _ in $(seq 1 20); do
  if curl -fsS "http://127.0.0.1:${PORT}/api/sys_check" >/dev/null; then
    break
  fi
  sleep 2
done

set -a
source .env.production
set +a
APP_URL="http://127.0.0.1:${PORT}" PORT="${PORT}" bash scripts/configure-runtime.sh

curl -fsS "http://127.0.0.1:${PORT}/api/sys_check" >/dev/null
systemctl --no-pager --full status "${SERVICE_NAME}" | head -n 20
