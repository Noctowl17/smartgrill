#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
USER_NAME="${SUDO_USER:-$USER}"
GROUP_NAME="$(id -gn "$USER_NAME")"

cd "$ROOT"
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

if [[ ! -f .env ]]; then
  cp .env.example .env
fi

sed \
  -e "s|__USER__|$USER_NAME|g" \
  -e "s|__GROUP__|$GROUP_NAME|g" \
  -e "s|__DIR__|$ROOT|g" \
  systemd/smartgrill.service.template | sudo tee /etc/systemd/system/smartgrill.service >/dev/null

sudo systemctl daemon-reload
sudo systemctl enable --now smartgrill

echo
echo "SmartGrill is geinstalleerd."
echo "Dashboard: http://$(hostname -I | awk '{print $1}'):8000"
echo "Status: sudo systemctl status smartgrill"
echo "Logs: journalctl -u smartgrill -f"
