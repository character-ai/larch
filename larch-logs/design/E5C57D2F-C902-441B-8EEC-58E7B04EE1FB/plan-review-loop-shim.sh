#!/usr/bin/env bash
# plan-review-loop-shim.sh — session-scoped workaround for larch plugin 47.0.19.
#
# Bug: skills/design/scripts/run-step3-review.sh:210 forwards --convergence-threshold
# to plan-review-loop.sh, but that script's argv parser (post-#3243) has no
# --convergence-threshold case and rejects unknown options via its `*)` catch-all
# (exit 2). Step 3 plan review then fails with panel-failed and Gate B is skipped.
#
# run-step3-review.sh:195 honors the RUN_STEP3_PLAN_REVIEW_LOOP_SH override hook,
# defaulting to the bundled plan-review-loop.sh. Point that env var at this shim:
# it drops --convergence-threshold (and its value) and forwards every other
# argument unchanged to the real bundled plan-review-loop.sh.
set -uo pipefail

REAL="<OPERATOR_REPO_PATH>/plugins/cache/larch-local/larch/47.0.19/skills/design/scripts/plan-review-loop.sh"
[ -x "$REAL" ] || { printf 'plan-review-loop-shim: real loop not executable: %s\n' "$REAL" >&2; exit 2; }

args=()
while [ "$#" -gt 0 ]; do
  case "$1" in
    --convergence-threshold)
      shift
      [ "$#" -gt 0 ] && shift   # also drop the value, when present
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
