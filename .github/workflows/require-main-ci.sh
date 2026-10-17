#!/usr/bin/env bash
# Check the newest push run, not a historical success before a failing rerun.
set -euo pipefail
commit=$(git rev-parse HEAD)
runs=$(gh api --method GET "repos/$GH_REPO/actions/workflows/ci.yml/runs" \
  -f branch=main -f event=push -f head_sha="$commit" -f per_page=100)
printf '%s' "$runs" | jq -e --arg commit "$commit" '
  [.workflow_runs[] | select(.head_sha == $commit and .head_branch == "main" and .event == "push")]
  | sort_by(.created_at, .id) | last
  | .status == "completed" and .conclusion == "success"
' || {
  echo "Release refused: the tagged commit needs a completed, successful CI push run on main." >&2
  exit 1
}
