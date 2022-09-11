#!/usr/bin/env bash
# Updates requirements.txt dependencies to the latest versions.

set -euo pipefail
cd "$(dirname "$0")/.."

rm -rf venv
python3.10 -m venv venv
# shellcheck disable=SC1091
source venv/bin/activate
python --version
python -m pip install --upgrade pip
python -m pip install .
rm -rf build
rm -rf api/games_fastapi.egg-info
pip uninstall -y Games-FastAPI
pip freeze > requirements.txt
