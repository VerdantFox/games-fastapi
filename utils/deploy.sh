#!/usr/bin/env bash
# This script performs the following actions:
#   - Fetches and rebases the latest release-branch from github
#   - Updates the crontab
#   - Restarts the production docker containers (with options)
#
# When writing crontab lines, append
# '>> "$(pwd)/logs/$(date +"%Y-%m-%d")_crontab.log"  2>&1'
# to commands to log output to a log file

set -euo pipefail
cd "$(dirname "$0")/.." || return

# ---------------------------------------------------------------------------
# GLOBALS
# ---------------------------------------------------------------------------
# crontab can't find docker compose without PATH defined
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/usr/local/games:/snap/bin
# Needed for correct timezone with 'date' calls
export TZ=America/Denver
DATE="$(date +"%Y-%m-%d")"
CRON_LOG="$(pwd)/logs/${DATE}_crontab.log"
NGINX_LOG="$(pwd)/logs/${DATE}_nginx.log"
FASTAPI_LOG="$(pwd)/logs/${DATE}_fastapi.log"
POSTGRES_LOG="$(pwd)/logs/${DATE}_postgres.log"
if [[ -z "${FROM_SCRATCH:-}" ]]
then
    unset BUILD_EXTRAS
else
    BUILD_EXTRAS=( "--no-cache" "--pull" )
fi
COMPOSE_EXTRAS=( "--file=docker/docker-compose.yaml" "--project-directory=." )

# ---------------------------------------------------------------------------
# FUNCTIONS
# ---------------------------------------------------------------------------
log() {
    level="$1"
    message="$2"
    echo "$(date "+%Y-%m-%d %H:%M:%S,%3N") [deploy.sh] [$level] $message"
}

# ---------------------------------------------------------------------------
# SCRIPT START
# ---------------------------------------------------------------------------
log INFO "Running utils/deploy.sh with vars: FROM_SCRATCH=${FROM_SCRATCH:-}, IF_NEEDED=${IF_NEEDED:-}, PROD=${PROD:-}"

# Set up log for crontab jobs (including deployment log)
mkdir -p "$(pwd)/logs"

# By default, don't checkout updated 'release-branch' before deploying
# (if PROD=1, then we do checkout the latest release-branch)
if [ "${PROD:-}" == "1" ]
then
    log INFO "Rebasing latest release-branch..."
    git fetch origin --prune
    checkout_result="$(git checkout release-branch)"
    echo "$checkout_result"
    if [[ "$checkout_result" == *"Your branch is up to date with 'origin/release-branch'."* && "${IF_NEEDED:-}" == "1" ]]; then
        # Nothing to do then.
        exit 0
    fi
    git rebase
fi


# By default, don't install the crontab that runs cron jobs
# (if PROD=1, then we do install.)
# Can use `crontab -l` to check if the crontab exists and `crontab -r` to remove the crontab.
# Crontab has 3 jobs:
# - Every 5 minutes run this deploy script, only if the 'release-branch' has changed
# - 1x per day run this deploy script to rebuild the docker images from scratch (to get latest security patches)
# - 1x per day delete > 1 week old logs from the 'logs/' directory
if [ "${PROD:-}" == "1" ]
then
touch "$CRON_LOG"
log INFO "Installing new crontab..."
crontab << ENDCRON
# Games-FastAPI scheduled tasks
# This crontab was generated automatically and should not be edited.
# Deploy (from scratch): every day at 2:07AM.
7 2 * * * PATH=$PATH TZ=America/Denver FROM_SCRATCH=1 PROD=1 "$(pwd)/utils/deploy.sh" >> "$CRON_LOG"  2>&1
# Deploy (only if needed): every 5 minutes.
*/5 * * * * PATH=$PATH TZ=America/Denver IF_NEEDED=1 PROD=1 "$(pwd)/utils/deploy.sh" >> "$CRON_LOG"  2>&1
# Remove week-old logs: every day at 3:07AM.
7 3 * * * find "$(pwd)/logs/" -mtime +7  -exec rm {} \; >> "$CRON_LOG"  2>&1
ENDCRON
fi

log INFO "Building latest images..."
# shellcheck disable=SC2068
docker compose ${COMPOSE_EXTRAS[@]:-} build ${BUILD_EXTRAS[@]:-}

log INFO "Stopping and removing containers..."
# shellcheck disable=SC2068
docker compose ${COMPOSE_EXTRAS[@]:-} down

log INFO "Starting containers..."
# shellcheck disable=SC2068
docker compose ${COMPOSE_EXTRAS[@]:-} up --detach

log INFO "Removing dangling images..."
docker image prune --force

log INFO "Establishing docker container logging..."
# Logs dir created earlier, so no need to re-create here
touch "$NGINX_LOG"
docker logs --follow nginx &>> "$NGINX_LOG" &
touch "$FASTAPI_LOG"
docker logs --follow fastapi &>> "$FASTAPI_LOG" &
touch "$POSTGRES_LOG"
docker logs --follow postgres &>> "$POSTGRES_LOG" &
