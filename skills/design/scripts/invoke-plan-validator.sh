#!/usr/bin/env bash
# Pipe ACTION=VALIDATE_PLAN_COMMANDS to design-driver.sh.
# Prints driver stdout (KV lines).
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd -P)
PLAN_FILE="${1:?usage: invoke-plan-validator.sh PLAN_FILE}"

: "${DESIGN_TMPDIR:?DESIGN_TMPDIR must be set}"
: "${CLAUDE_PLUGIN_ROOT:?CLAUDE_PLUGIN_ROOT must be set}"

printf 'ACTION=VALIDATE_PLAN_COMMANDS ARGS=%s %s\n' \
    "$(printf '%q' --plan-file)" \
    "$(printf '%q' "$PLAN_FILE")" \
    | "$SCRIPT_DIR/design-driver.sh" --design-tmpdir "$DESIGN_TMPDIR"
