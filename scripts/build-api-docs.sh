#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SITE_DIR="$ROOT_DIR/site"
PYTHON_BIN="${PYTHON_BIN:-python3}"

if [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
  PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
fi

"$PYTHON_BIN" "$ROOT_DIR/scripts/export_openapi.py"
mkdir -p "$SITE_DIR"
npx --yes @redocly/cli@2.25.2 build-docs \
  "$ROOT_DIR/docs/openapi.json" \
  --config "$ROOT_DIR/docs/redocly.yaml" \
  --output "$SITE_DIR/index.html" \
  --title "linkTranscriber API Docs"

printf 'linktranscriber-docs\n' > "$SITE_DIR/.nojekyll"
echo "Static API docs built in $SITE_DIR"
