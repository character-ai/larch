#!/usr/bin/env bash
# gather-branch-context.sh — Gather git diff, file list, and commit log for
# the current branch vs main.
#
# Writes each output to a separate file in the specified output directory,
# then emits the file paths as key=value output to stdout.
#
# Usage:
#   gather-branch-context.sh --output-dir <path>
#
# Arguments:
#   --output-dir — Directory to write output files into (must exist)
#
# Creates:
#   <output-dir>/diff.txt      — Diff with 20 lines of context per hunk (git diff -U20 MERGE_BASE...HEAD)
#   <output-dir>/file-list.txt — Changed file names (git diff MERGE_BASE...HEAD --name-only)
#   <output-dir>/commit-log.txt — Commit log (git log MERGE_BASE..HEAD --oneline)
#
# Outputs (key=value to stdout):
#   DIFF_FILE=<path>
#   FILE_LIST_FILE=<path>
#   COMMIT_LOG_FILE=<path>
#   COMMIT_COUNT=<n>   — number of commits on the branch vs main
#
# Exit codes:
#   0 — success
#   1 — usage/argument error or git command failure

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init

usage() { larch_err "Usage: gather-branch-context.sh --output-dir <path>"; }

# --- Parse arguments ---
OUTPUT_DIR=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --output-dir) OUTPUT_DIR="${2:?--output-dir requires a value}"; shift 2 ;;
        --help) usage; exit 0 ;;
        *) larch_err "Unknown option: $1"; usage; exit 1 ;;
    esac
done

if [[ -z "$OUTPUT_DIR" ]]; then
    larch_err "ERROR: --output-dir is required"
    usage; exit 1
fi

if [[ ! -d "$OUTPUT_DIR" ]]; then
    larch_err "ERROR: output directory does not exist: $OUTPUT_DIR"
    exit 1
fi

# --- Gather context ---
DIFF_FILE="$OUTPUT_DIR/diff.txt"
FILE_LIST_FILE="$OUTPUT_DIR/file-list.txt"
COMMIT_LOG_FILE="$OUTPUT_DIR/commit-log.txt"

MERGE_BASE=$(git merge-base HEAD main)
git diff -U20 "${MERGE_BASE}"...HEAD -- . ':(exclude)larch-logs/**' > "$DIFF_FILE"
git diff "${MERGE_BASE}"...HEAD --name-only -- . ':(exclude)larch-logs/**' > "$FILE_LIST_FILE"
git log "${MERGE_BASE}"..HEAD --oneline -- . ':(exclude)larch-logs/**' > "$COMMIT_LOG_FILE"
COMMIT_COUNT=$(wc -l < "$COMMIT_LOG_FILE" | tr -d ' ')

# --- Emit output ---
emit_kv DIFF_FILE "$DIFF_FILE"
emit_kv FILE_LIST_FILE "$FILE_LIST_FILE"
emit_kv COMMIT_LOG_FILE "$COMMIT_LOG_FILE"
emit_kv COMMIT_COUNT "$COMMIT_COUNT"
