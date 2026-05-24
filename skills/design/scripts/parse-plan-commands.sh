#!/usr/bin/env bash
# Parse /design plan markdown: fenced bash/sh blocks → command TSV (see parse-plan-commands.md).

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd -P)
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/../../../scripts/lib-quiet.sh"
larch_quiet_init

PLAN_FILE=""
OUTPUT_FILE=""
REPO_ROOT=""

usage() {
    while IFS= read -r line; do larch_err "$line"; done <<'USAGE'
usage: parse-plan-commands.sh --plan-file FILE --output FILE [--repo-root DIR]
USAGE
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --plan-file)
            PLAN_FILE="${2:?--plan-file requires a value}"
            shift 2
            ;;
        --output)
            OUTPUT_FILE="${2:?--output requires a value}"
            shift 2
            ;;
        --repo-root)
            REPO_ROOT="${2:?--repo-root requires a value}"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            larch_err "parse-plan-commands.sh: unknown argument: $1"
            usage
            exit 2
            ;;
    esac
done

if [[ -z "$PLAN_FILE" || -z "$OUTPUT_FILE" ]]; then
    larch_err "parse-plan-commands.sh: --plan-file and --output are required"
    usage
    exit 2
fi
if [[ ! -r "$PLAN_FILE" ]]; then
    larch_err "parse-plan-commands.sh: plan file missing or unreadable: $PLAN_FILE"
    exit 2
fi

if [[ -z "$REPO_ROOT" ]]; then
    REPO_ROOT=$(git -C "$SCRIPT_DIR/../../.." rev-parse --show-toplevel 2>/dev/null || true)
fi
if [[ -z "$REPO_ROOT" ]]; then
    REPO_ROOT=$(pwd -P)
fi
REPO_ROOT=${REPO_ROOT%/}

plugin_root="${CLAUDE_PLUGIN_ROOT:-$REPO_ROOT}"
plugin_root=${plugin_root%/}

tmp_out=$(mktemp "${OUTPUT_FILE}.tmp.XXXXXX")
# shellcheck disable=SC2317  # cleanup is invoked via EXIT trap only
cleanup() { rm -f "$tmp_out"; }
trap cleanup EXIT

awk -v REPO_ROOT="$REPO_ROOT" -v PLUGIN_ROOT="$plugin_root" \
    -f "$SCRIPT_DIR/parse-plan-commands.awk" "$PLAN_FILE" >"$tmp_out"

mv "$tmp_out" "$OUTPUT_FILE"
trap - EXIT

exit 0
