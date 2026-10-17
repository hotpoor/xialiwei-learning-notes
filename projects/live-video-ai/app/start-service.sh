#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [ "$(ps -p 1 -o comm=)" != systemd ]; then
  echo 'WSL systemd is unavailable; use the foreground uvicorn command in README.' >&2
  exit 1
fi
if systemctl is-active --quiet liveai-style-v1.service; then
  echo 'liveai-style-v1 is already running.'
  exit 0
fi
systemd-run --unit=liveai-style-v1 --collect \
  --property="WorkingDirectory=$PWD" \
  --setenv=HF_HUB_OFFLINE=1 --setenv=TRANSFORMERS_OFFLINE=1 \
  "$PWD/.venv/bin/python" -m uvicorn server:app \
  --host 127.0.0.1 --port 8767 --ws-max-size 2100000
# Transient service: survives SSH disconnect, stops on WSL shutdown; no boot autostart.
