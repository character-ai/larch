#!/usr/bin/env bash
# Session-local workaround for the #3274 convergence-threshold forwarding regression.
# run-step3-review.sh forwards --convergence-threshold to plan-review-loop.sh, which
# rejects unknown options (exit 2). #3265 made convergence a hardcoded single-round rule
# (CONVERGENCE_NON_NIT_MAX), so the flag is a no-op. This shim strips it and forwards the
# rest to the real plan-review-loop.sh. It mutates NO repo files; it is wired in only via
# the documented RUN_STEP3_PLAN_REVIEW_LOOP_SH override hook for this one /design run.
set -euo pipefail

REAL_LOOP="<OPERATOR_REPO_PATH>/plugins/cache/larch-local/larch/47.0.19/skills/design/scripts/plan-review-loop.sh"

args=()
skip_next=0
for a in "$@"; do
    if [ "$skip_next" -eq 1 ]; then
        skip_next=0
        continue
    fi
    case "$a" in
        --convergence-threshold)
            skip_next=1
            continue
            ;;
        --convergence-threshold=*)
            continue
            ;;
    esac
    args+=("$a")
done

if [ "${#args[@]}" -gt 0 ]; then
    exec "$REAL_LOOP" "${args[@]}"
else
    exec "$REAL_LOOP"
fi
