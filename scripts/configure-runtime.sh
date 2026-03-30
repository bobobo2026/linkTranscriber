#!/usr/bin/env bash
set -euo pipefail

APP_URL="${APP_URL:-http://127.0.0.1:${PORT:-18001}}"
TRANSCRIBER_TYPE="${TRANSCRIBER_TYPE:-bcut}"
WHISPER_MODEL_SIZE="${WHISPER_MODEL_SIZE:-base}"

json_escape() {
  python3 - <<'PY'
import json, os
print(json.dumps(os.environ["VALUE"], ensure_ascii=False))
PY
}

curl_json() {
  local url="$1"
  local body="$2"
  curl -fsS -X POST "$url" \
    -H 'Content-Type: application/json' \
    -d "$body" >/dev/null
}

curl_json "${APP_URL}/api/transcriber_config" \
  "{\"transcriber_type\":\"${TRANSCRIBER_TYPE}\",\"whisper_model_size\":\"${WHISPER_MODEL_SIZE}\"}"

if [[ -n "${DOUYIN_COOKIE:-}" ]]; then
  export VALUE="${DOUYIN_COOKIE}"
  cookie_json="$(json_escape)"
  curl_json "${APP_URL}/api/update_downloader_cookie" \
    "{\"platform\":\"douyin\",\"cookie\":${cookie_json}}"
fi

if [[ -n "${DEEPSEEK_API_KEY:-}" ]]; then
  export VALUE="${DEEPSEEK_API_KEY}"
  deepseek_key_json="$(json_escape)"
  curl_json "${APP_URL}/api/update_provider" \
    "{\"id\":\"deepseek\",\"name\":\"DeepSeek\",\"api_key\":${deepseek_key_json},\"base_url\":\"https://api.deepseek.com\",\"type\":\"built-in\",\"enabled\":1}"
  curl_json "${APP_URL}/api/models" \
    "{\"provider_id\":\"deepseek\",\"model_name\":\"deepseek-chat\"}" || true
fi

curl -fsS "${APP_URL}/api/sys_check" >/dev/null
