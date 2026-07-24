#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
USER_NAME="${SUDO_USER:-$USER}"
GROUP_NAME="$(id -gn "$USER_NAME")"
VENV="$ROOT/.venv"
SERVICE_TEMPLATE="$ROOT/systemd/smartgrill.service.template"
SERVICE_FILE="/etc/systemd/system/smartgrill.service"

info() {
  printf '\n==> %s\n' "$1"
}

warn() {
  printf '\nWarning: %s\n' "$1" >&2
}

fail() {
  printf '\nError: %s\n' "$1" >&2
  exit 1
}

command -v python3 >/dev/null 2>&1 || fail "python3 is not installed"
[[ -f "$ROOT/requirements.txt" ]] || fail "requirements.txt is missing"
[[ -f "$ROOT/.env.example" ]] || fail ".env.example is missing"
[[ -f "$SERVICE_TEMPLATE" ]] || fail "systemd service template is missing"

cd "$ROOT"

info "Preparing Bluetooth"
if command -v rfkill >/dev/null 2>&1; then
  if rfkill list bluetooth >/dev/null 2>&1; then
    if rfkill list bluetooth | grep -q "Soft blocked: yes"; then
      rfkill unblock bluetooth || warn "Bluetooth could not be unblocked automatically"
    fi

    if rfkill list bluetooth | grep -q "Hard blocked: yes"; then
      warn "Bluetooth is hard blocked and must be enabled manually"
    fi
  else
    warn "No Bluetooth adapter was found by rfkill"
  fi
else
  warn "rfkill is not installed; Bluetooth block status could not be checked"
fi

if systemctl list-unit-files bluetooth.service >/dev/null 2>&1; then
  systemctl enable --now bluetooth.service || warn "Bluetooth service could not be enabled"
fi

info "Creating Python virtual environment"
if [[ ! -x "$VENV/bin/python" ]]; then
  sudo -u "$USER_NAME" python3 -m venv "$VENV"
fi

info "Installing Python dependencies"
sudo -u "$USER_NAME" "$VENV/bin/python" -m pip install --upgrade pip
sudo -u "$USER_NAME" env AIOHTTP_NO_EXTENSIONS=1 "$VENV/bin/pip" install -r requirements.txt

if [[ ! -f "$ROOT/.env" ]]; then
  info "Creating .env from .env.example"
  sudo -u "$USER_NAME" cp "$ROOT/.env.example" "$ROOT/.env"
  printf '\nEdit %s and set the Bluetooth MAC address before normal use.\n' "$ROOT/.env"
fi

info "Installing systemd service"
sed \
  -e "s|__USER__|$USER_NAME|g" \
  -e "s|__GROUP__|$GROUP_NAME|g" \
  -e "s|__DIR__|$ROOT|g" \
  "$SERVICE_TEMPLATE" | tee "$SERVICE_FILE" >/dev/null

systemctl daemon-reload
systemctl enable --now smartgrill

IP_ADDRESS="$(hostname -I 2>/dev/null | awk '{print $1}')"
PORT="$(sed -n 's/^SMARTGRILL_PORT=//p' "$ROOT/.env" | tail -n 1)"
PORT="${PORT:-8000}"

printf '\nSmartGrill is installed and running.\n'
printf 'Dashboard: http://%s:%s\n' "${IP_ADDRESS:-IP-ADDRESS}" "$PORT"
printf 'Status: sudo systemctl status smartgrill\n'
printf 'Logs: journalctl -u smartgrill -f\n'