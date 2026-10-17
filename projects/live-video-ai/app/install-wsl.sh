#!/usr/bin/env bash
# Run only in the dedicated project directory, not in an existing project's venv.
set -euo pipefail
cd "$(dirname "$0")"
if [ ! -e .venv ]; then python3 -m venv .venv; fi
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install torch==2.7.1 torchvision==0.22.1 --index-url https://download.pytorch.org/whl/cu126
.venv/bin/python -m pip install -r requirements.in
.venv/bin/python verify_cuda.py
.venv/bin/python -m pip freeze > requirements.lock.txt
