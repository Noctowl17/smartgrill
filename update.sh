#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
USER_NAME="${SUDO_USER:-$USER}"
GROUP_NAME="$(id -gn "$USER_NAME")"
VENV="$ROOT/.venv"
SERVICE_TEMPLATE="$ROOT/systemd/smartgrill.service.template"
SERVICE_FILE="/etc/systemd/system/smartgrill.service"

fail() {
  printf 'Error: %s\n' "$1" >&2
  exit 1
}

[[ -d "$ROOT/.git" ]] || fail "this directory is not a Git repository"
[[ -x "$VENV/bin/pip" ]] || fail ".venv is missing; run install.sh first"
[[ -f "$ROOT/.env" ]] || fail ".env is missing; copy .env.example to .env"
[[ -f "$SERVICE_TEMPLATE" ]] || fail "systemd service template is missing"

cd "$ROOT"

echo "==> Pulling latest changes"
git pull --ff-only

echo "==> Updating Python dependencies"
sudo -u "$USER_NAME" "$VENV/bin/pip" install -r requirements.txt

echo "==> Updating systemd service"
sed \
  -e "s|__USER__|$USER_NAME|g" \
  -e "s|__GROUP__|$GROUP_NAME|g" \
  -e "s|__DIR__|$ROOT|g" \
  "$SERVICE_TEMPLATE" | sudo tee "$SERVICE_FILE" >/dev/null

sudo systemctl daemon-reload
sudo systemctl restart smartgrill
sudo systemctl --no-pager --full status smartgrill
