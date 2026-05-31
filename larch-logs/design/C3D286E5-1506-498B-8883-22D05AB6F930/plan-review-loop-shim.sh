#!/usr/bin/env bash
# Session-local shim for larch 47.0.19 Step-3 argv drift (run-step3-review.sh
# forwards --convergence-threshold, which plan-review-loop.sh rejected after
# #3243 relaxed convergence). Drops --convergence-threshold <value> and forwards
# the rest to the real loop. No plugin files are modified; pointed at via the
# driver's documented RUN_STEP3_PLAN_REVIEW_LOOP_SH override hook.
set -euo pipefail
REAL="<OPERATOR_REPO_PATH>/plugins/cache/larch-local/larch/47.0.19/skills/design/scripts/plan-review-loop.sh"
args=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --convergence-threshold)
      if [[ $# -ge 2 ]]; then shift 2; else shift; fi
      ;;
    *)
      args+=("$1")
      shift
      ;;
  esac
done
exec "$REAL" ${args[@]+"${args[@]}"}
