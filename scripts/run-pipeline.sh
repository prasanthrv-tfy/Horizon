#!/usr/bin/env bash
# Full Horizon pipeline: fetch → blog generation → publish
# Usage: ./scripts/run-pipeline.sh [--hours 24] [--profile all] [--dry-run]
# Cron:  0 8 * * * /path/to/horizon/scripts/run-pipeline.sh >> /path/to/horizon/logs/cron.log 2>&1

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_PREFIX="[$(date '+%Y-%m-%d %H:%M:%S')]"

# Defaults
HOURS=24
PROFILE="engineer"
DRY_RUN=false

# Parse args
while [[ $# -gt 0 ]]; do
  case "$1" in
    --hours)   HOURS="$2";   shift 2 ;;
    --profile) PROFILE="$2"; shift 2 ;;
    --dry-run) DRY_RUN=true; shift   ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

cd "$PROJECT_DIR"

log() { echo "$LOG_PREFIX $*"; }

log "Starting full Horizon pipeline (hours=$HOURS, profile=$PROFILE, dry_run=$DRY_RUN)"

# 1. Fetch & score
log "Stage 1/3: horizon (fetch + score + enrich)"
uv run horizon --hours "$HOURS"

# 2. Blog generation
log "Stage 2/3: horizon-blog (generate posts, profile=$PROFILE)"
uv run horizon-blog --profile "$PROFILE"

# 3. Publish
if [[ "$DRY_RUN" == true ]]; then
  log "Stage 3/3: skipped (--dry-run)"
else
  log "Stage 3/3: horizon-publish (deduplicate + push to Webflow)"
  uv run horizon-publish
fi

log "Pipeline complete."