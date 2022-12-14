#!/usr/bin/env bash
# Updates requirements.txt dependencies to the latest versions.
# shellcheck disable=SC2129

set -euo pipefail
cd "$(dirname "$0")/.."

# Setup and upgrade virtual environment in (venv) directory.
rm -rf venv
python3.10 -m venv venv
# shellcheck disable=SC1091
source venv/bin/activate
python --version
python -m pip install --upgrade pip
# Install production dependencies and write them to requirements-prod.txt.
python -m pip install .
pip uninstall -y Games-FastAPI
echo "# requirements-prod.txt: production requirements file." > requirements-prod.txt
echo "# This file was auto-generated by utils/update-requirements.sh." >> requirements-prod.txt
echo "# The conents of this file are a subset of requirements-dev.txt." >> requirements-prod.txt
pip freeze >> requirements-prod.txt
# Install development dependencies and write them to requirements-dev.txt.
python -m pip install .[dev]
pip uninstall -y Games-FastAPI
echo "# requirements-dev.txt: development python requirements file." > requirements-dev.txt
echo "# This file was auto-generated by utils/update-requirements.sh." >> requirements-dev.txt
echo "# The conents of this file are a superset of requirements-prod.txt." >> requirements-dev.txt
pip freeze >> requirements-dev.txt
# Cleanup installation files
rm -rf build
rm -rf api/games_fastapi.egg-info
