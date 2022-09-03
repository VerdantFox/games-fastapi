#!/usr/bin/env bash
# Run the pre-commit checks right now

cd "$(dirname "$0")/.."
set -euo pipefail

pre-commit install
pre-commit run --all-files
