#!/usr/bin/env bash
# Full Horizon pipeline: fetch → blog generation → publish → upload artifacts
# Usage: ./scripts/run-pipeline.sh [--hours 24] [--profile all] [--max-posts 4] [--publish live] [--max-publish 2] [--dry-run]
# Env:   ARTIFACTS_ML_REPO — TrueFoundry ML repo name for artifact upload (skipped if unset)
# Cron:  0 8 * * * /path/to/horizon/scripts/run-pipeline.sh >> /path/to/horizon/logs/cron.log 2>&1

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_PREFIX="[$(date '+%Y-%m-%d %H:%M:%S')]"

# Defaults
HOURS=24
PROFILE="engineer"
MAX_POSTS=""
PUBLISH=""
MAX_PUBLISH=""
DRY_RUN=false
REPO_NAME="${ARTIFACTS_ML_REPO:-}"

# Parse args
while [[ $# -gt 0 ]]; do
  case "$1" in
    --hours)        HOURS="$2";       shift 2 ;;
    --profile)      PROFILE="$2";     shift 2 ;;
    --max-posts)    MAX_POSTS="$2";   shift 2 ;;
    --publish)      PUBLISH="$2";     shift 2 ;;
    --max-publish)  MAX_PUBLISH="$2"; shift 2 ;;
    --dry-run)      DRY_RUN=true;     shift   ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

cd "$PROJECT_DIR"

log() { echo "$LOG_PREFIX $*"; }

log "Starting full Horizon pipeline (hours=$HOURS, profile=$PROFILE, max_posts=${MAX_POSTS:-default}, publish=${PUBLISH:-default}, max_publish=${MAX_PUBLISH:-default}, dry_run=$DRY_RUN)"

# 1. Fetch & score
log "Stage 1/4: horizon (fetch + score + enrich)"
uv run horizon --hours "$HOURS"

# 2. Blog generation
log "Stage 2/4: horizon-blog (generate posts, profile=$PROFILE)"
BLOG_ARGS=(--profile "$PROFILE")
[[ -n "$MAX_POSTS" ]] && BLOG_ARGS+=(--max-posts "$MAX_POSTS")
uv run horizon-blog "${BLOG_ARGS[@]}"

# 3. Publish
if [[ "$DRY_RUN" == true ]]; then
  log "Stage 3/4: skipped (--dry-run)"
else
  log "Stage 3/4: horizon-publish (deduplicate + push to Webflow)"
  PUBLISH_ARGS=()
  [[ -n "$PUBLISH" ]] && PUBLISH_ARGS+=(--publish "$PUBLISH")
  [[ -n "$MAX_PUBLISH" ]] && PUBLISH_ARGS+=(--max-publish "$MAX_PUBLISH")
  uv run horizon-publish "${PUBLISH_ARGS[@]}"
fi

# 4. Upload artifacts
if [[ -z "$REPO_NAME" ]]; then
  log "Stage 4/4: skipped (no ARTIFACTS_ML_REPO set)"
elif [[ "$DRY_RUN" == true ]]; then
  log "Stage 4/4: skipped (--dry-run)"
else
  log "Stage 4/4: horizon-upload-artifacts (repo=$REPO_NAME)"
  uv run horizon-upload-artifacts --repo-name "$REPO_NAME"
fi

log "Pipeline complete."