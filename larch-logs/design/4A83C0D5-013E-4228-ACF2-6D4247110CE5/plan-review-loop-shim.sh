#!/usr/bin/env bash
# Session-local workaround shim for plugin 47.0.19 Step-3 argv mismatch.
#
# run-step3-review.sh passes --convergence-threshold to plan-review-loop.sh, but
# plan-review-loop.sh (post-#3243) no longer accepts that flag and rejects unknown
# options with exit 2 — so the panel fails on every /design run. This shim strips
# the one stale flag and forwards the remaining (all-accepted) args to the real
# plugin plan-review-loop.sh. It does NOT modify the installed plugin or the repo;
# it is wired in only via RUN_STEP3_PLAN_REVIEW_LOOP_SH for this session.
set -euo pipefail

REAL="<OPERATOR_REPO_PATH>/plugins/cache/larch-local/larch/47.0.19/skills/design/scripts/plan-review-loop.sh"

args=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --convergence-threshold)
      shift
      [[ $# -gt 0 ]] && shift   # drop the flag's value when present
      ;;
    --convergence-threshold=*)
      shift
      ;;
    *)
      args+=("$1")
      shift
      ;;
  esac
done

exec "$REAL" ${args[@]+"${args[@]}"}
