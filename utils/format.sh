#!/usr/bin/env bash
# format: run auto-formatting utilities isort and black
# This runs in an order that will satisfy utils/test.sh checks.

cd "$(dirname "$0")/.."
set -euo pipefail

echo "Sorting python imports with isort."
isort .

echo "Auto-formatting python code with black."
black .
