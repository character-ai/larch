#!/usr/bin/env bash
# Driver: parse plan → validate commands; copy log to DESIGN_TMPDIR (see validate-plan.md).
# Tier2+opt-in Tier3 plan-command validation driver for ACTION=VALIDATE_PLAN_COMMANDS.

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd -P)
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/../../../scripts/lib-quiet.sh"
larch_quiet_init

PLAN_FILE=""
REPO_ROOT=""

usage() {
    while IFS= read -r line; do larch_err "$line"; done <<'USAGE'
usage: validate-plan.sh --plan-file FILE [--repo-root DIR]
USAGE
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --plan-file)
            PLAN_FILE="${2:?}"
            shift 2
            ;;
        --repo-root)
            REPO_ROOT="${2:?}"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            larch_err "validate-plan.sh: unknown argument: $1"
            usage
            exit 2
            ;;
    esac
done

if [[ -z "$PLAN_FILE" ]]; then
    larch_err "validate-plan.sh: --plan-file is required"
    usage
    exit 2
fi
if [[ ! -r "$PLAN_FILE" ]]; then
    larch_err "validate-plan.sh: unreadable plan file: $PLAN_FILE"
    exit 2
fi

if [[ -z "$REPO_ROOT" ]]; then
    REPO_ROOT=$(git -C "$SCRIPT_DIR/../../.." rev-parse --show-toplevel 2>/dev/null || pwd -P)
fi
REPO_ROOT=${REPO_ROOT%/}

base=$(basename "$PLAN_FILE")
source_kind="plan"
if [[ "$base" == "composed-plan.md" ]]; then
    source_kind="composed"
fi

tsv=$(mktemp "${TMPDIR:-/tmp}/larch-validate-plan.XXXXXX.tsv")
logtmp=$(mktemp "${TMPDIR:-/tmp}/larch-validate-plan.XXXXXX.log")
trap 'rm -f "$tsv" "$logtmp"' EXIT

"$SCRIPT_DIR/parse-plan-commands.sh" --plan-file "$PLAN_FILE" --output "$tsv" --repo-root "$REPO_ROOT"

"$SCRIPT_DIR/validate-plan-commands.sh" \
    --tsv-file "$tsv" \
    --log-file "$logtmp" \
    --source-kind "$source_kind"

last=$(tail -n 1 "$logtmp")
IFS=$'\t' read -r -a kv_parts <<<"$last" || true
for pair in "${kv_parts[@]}"; do
    [[ -z "$pair" ]] && continue
    k="${pair%%=*}"
    v="${pair#*=}"
    case "$k" in
        VALIDATE_STATUS) emit_kv VALIDATE_STATUS "$v" ;;
        DEFECT_COUNT) emit_kv VALIDATE_DEFECT_COUNT "$v" ;;
        SKIPPED_COUNT) emit_kv VALIDATE_SKIPPED_COUNT "$v" ;;
        UNSAFE_TOKEN_COUNT) emit_kv VALIDATE_UNSAFE_TOKEN_COUNT "$v" ;;
    esac
done

if [[ -n "${DESIGN_TMPDIR:-}" && -d "$DESIGN_TMPDIR" ]]; then
    cp "$logtmp" "$DESIGN_TMPDIR/validate-plan-commands.log"
    emit_kv VALIDATE_LOG_FILE "$DESIGN_TMPDIR/validate-plan-commands.log"
else
    emit_kv VALIDATE_LOG_FILE "$logtmp"
fi

exit 0
