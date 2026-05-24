#!/usr/bin/env bash
# When review_budget is not quick, pipe ACTION=VALIDATE_PLAN_COMMANDS to design-driver.sh.
# Prints driver stdout (KV lines). Prints nothing when validator is skipped (quick tier).
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd -P)
PLAN_FILE="${1:?usage: invoke-plan-validator-if-not-quick.sh PLAN_FILE}"

: "${DESIGN_TMPDIR:?DESIGN_TMPDIR must be set}"
: "${CLAUDE_PLUGIN_ROOT:?CLAUDE_PLUGIN_ROOT must be set}"

_review_budget=full
rp="$DESIGN_TMPDIR/run-params.json"
if [[ -r "$rp" ]]; then
    _review_budget=$("$SCRIPT_DIR/read-design-review-budget.sh" "$rp")
fi
if [[ "$_review_budget" == "quick" ]]; then
    exit 0
fi

printf 'ACTION=VALIDATE_PLAN_COMMANDS ARGS=--plan-file %s\n' "$PLAN_FILE" \
    | "$SCRIPT_DIR/design-driver.sh" --design-tmpdir "$DESIGN_TMPDIR"
