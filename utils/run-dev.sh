#!/usr/bin/env bash
# Run the app in development mode.

set -euo pipefail
cd "$(dirname "$0")/.."

uvicorn api.app:app --reload
