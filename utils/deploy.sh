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
# crontab can't find docker-compose without PATH defined
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/usr/local/games:/snap/bin
# Needed for correct timezone with 'date' calls
export TZ=America/Denver
CRON_LOG="$(pwd)/logs/$(date +"%Y-%m-%d")_crontab.log"

if [[ -z "${FROM_SCRATCH:-}" ]]
then
    unset BUILD_EXTRAS
else
    BUILD_EXTRAS=( "--no-cache" "--pull" )
fi

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
log INFO "Running utils/deploy.sh with vars: FROM_SCRATCH=${FROM_SCRATCH:-}, IF_NEEDED=${IF_NEEDED:-}"

# Set up log for crontab jobs (including deployment log)
mkdir -p "$(pwd)/logs"
touch "$CRON_LOG"

log INFO "Rebasing latest release-branch..."
git fetch origin --prune
checkout_result="$(git checkout release-branch)"
echo "$checkout_result"
if [[ "$checkout_result" == *"Your branch is up to date with 'origin/release-branch'."* && "${IF_NEEDED:-}" == "1" ]]; then
    # Nothing to do then.
    exit 0
fi
git rebase

log INFO "Installing new crontab..."
crontab << ENDCRON
# Games-FastAPI scheduled tasks
# This crontab was generated automatically and should not be edited.
# Deploy (from scratch): every day at 2:07AM.
7 2 * * * PATH=$PATH TZ=America/Denver FROM_SCRATCH=1 "$(pwd)/utils/deploy.sh" >> "$CRON_LOG"  2>&1
# Deploy (only if needed): every 5 minutes.
*/5 * * * * PATH=$PATH TZ=America/Denver IF_NEEDED=1 "$(pwd)/utils/deploy.sh" >> "$CRON_LOG"  2>&1
# Remove week-old logs: every day at 3:07AM.
7 3 * * * find "$(pwd)/logs/" -mtime +7  -exec rm {} \; >> "$CRON_LOG"  2>&1
ENDCRON

log INFO "Building latest images..."
# shellcheck disable=SC2068
docker compose build ${BUILD_EXTRAS[@]:-}

log INFO "Stopping and removing containers..."
docker compose down

log INFO "Starting containers..."
docker compose up --detach

log INFO "Removing dangling images..."
docker image prune --force
