#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
git pull --ff-only
.venv/bin/pip install -r requirements.txt
sudo systemctl restart smartgrill
