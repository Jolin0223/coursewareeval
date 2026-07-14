#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$ROOT_DIR/generation-runner/.env"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

if [[ -z "${KPM_APP_SECRET:-}" ]]; then
  echo "Missing KPM_APP_SECRET."
  echo "Create generation-runner/.env from generation-runner/.env.example and fill KPM_APP_SECRET first."
  exit 1
fi

cd "$ROOT_DIR"
python3 generation-runner/server.py
