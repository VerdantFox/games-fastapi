#!/usr/bin/env bash
# pytest: run pytests excluding integration pytests
#
# Assumes `requirements.txt` is pip installed in a virtual environment

cd "$(dirname "$0")/.."
set -euo pipefail

python -m pytest "$@" tests/
