#!/usr/bin/env bash
# gh-pr-body-update.sh — Update a PR's body from a file.
#
# Wraps `gh pr edit --body-file` with structured output. Uses --body-file
# only (not inline --body) to avoid shell argument length limits with
# large PR bodies.
#
# Usage:
#   gh-pr-body-update.sh --pr <number> --body-file <path> [--repo OWNER/REPO]
#
# Arguments:
#   --pr        — PR number
#   --body-file — Path to file containing the new PR body
#
# Outputs (key=value to stdout, always emitted via EXIT trap):
#   UPDATED=true|false
#   ERROR=<message>    (empty on success)
#
# Exit codes:
#   0 — update succeeded (UPDATED=true)
#   1 — usage/argument error (no output emitted)
#   2 — update failed (UPDATED=false, ERROR=<message> emitted via EXIT trap)

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init
# shellcheck source=scripts/lib-net.sh
source "$SCRIPT_DIR/lib-net.sh"

usage() { larch_err "Usage: gh-pr-body-update.sh --pr <number> --body-file <path> [--repo OWNER/REPO]"; }

PR=""
BODY_FILE=""
TARGET_REPO=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --pr) PR="${2:?--pr requires a value}"; shift 2 ;;
        --body-file) BODY_FILE="${2:?--body-file requires a value}"; shift 2 ;;
        --repo) TARGET_REPO="${2:?--repo requires a value}"; shift 2 ;;
        --help) usage; exit 0 ;;
        *) larch_err "Unknown option: $1"; usage; exit 1 ;;
    esac
done

if [[ -z "$PR" ]] || [[ -z "$BODY_FILE" ]]; then
    larch_err "ERROR: --pr and --body-file are required"
    usage; exit 1
fi

GH_REPO_ARGS=()
if [[ -n "$TARGET_REPO" ]]; then
    if [[ ! "$TARGET_REPO" =~ ^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$ ]]; then
        larch_err "ERROR: --repo must be OWNER/REPO using GitHub owner/repo characters"
        usage
        exit 1
    fi
    GH_REPO_ARGS=(--repo "$TARGET_REPO")
fi

# --- Output defaults ---
UPDATED="false"
ERROR="gh-pr-body-update.sh exited unexpectedly"

# shellcheck disable=SC2329,SC2317
emit_output() {
    emit_kv UPDATED "$UPDATED"
    emit_kv ERROR "$ERROR"
}
trap 'emit_output' EXIT

if [[ ! -f "$BODY_FILE" ]]; then
    ERROR="body file not found: $BODY_FILE"
    exit 2
fi

fail_file=$(mktemp "${TMPDIR:-/tmp}/gh-pr-body-update.XXXXXX")
if with_transient_retry transient_envelope_predicate_none "$fail_file" \
    gh pr edit "$PR" ${GH_REPO_ARGS[@]+"${GH_REPO_ARGS[@]}"} --body-file "$BODY_FILE"; then
    EXIT_CODE=0
else
    EXIT_CODE=$_WTR_RC
fi
OUTPUT=$(cat "$fail_file" 2>/dev/null || true)
rm -f "$fail_file"

if [[ $EXIT_CODE -eq 0 ]]; then
    UPDATED="true"
    ERROR=""
    exit 0
else
    UPDATED="false"
    OUTPUT="${OUTPUT//$'\n'/ }"
    ERROR="gh pr edit failed (exit $EXIT_CODE): $OUTPUT"
    exit 2
fi
