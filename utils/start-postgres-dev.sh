#!/usr/bin/env bash
# Start a local postgres docker container

set -euo pipefail
cd "$(dirname "$0")/.."

docker rm --force postgres > /dev/null 2>&1 || true
docker run --rm --detach --publish 5432:5432 --name postgres --env-file .env.dev postgres:13.3
