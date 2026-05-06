#!/usr/bin/env bash
# cleanup-tmpdir.sh — Safely remove a session temp directory.
#
# Validates that the path is non-empty and under /tmp/ (or /private/tmp/
# on macOS) before running rm -rf. This prevents accidental deletion of
# non-temp directories if the caller passes an empty or wrong path.
#
# Usage:
#   cleanup-tmpdir.sh --dir <path>
#
# Arguments:
#   --dir — Path to the temp directory to remove
#
# Exit codes:
#   0 — directory removed (or already absent)
#   1 — validation failed (path empty, not under /tmp/, or argument error)

set -euo pipefail

usage() { echo "Usage: cleanup-tmpdir.sh --dir <path>" >&2; }

DIR=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --dir) DIR="${2:?--dir requires a value}"; shift 2 ;;
        --help) usage; exit 0 ;;
        /tmp/*|/private/tmp/*) DIR="$1"; shift ;;
        *) echo "Unknown option: $1" >&2; usage; exit 1 ;;
    esac
done

if [[ -z "$DIR" ]]; then
    echo "ERROR: --dir is required and must be non-empty" >&2
    exit 1
fi

# Validate path is under /tmp/ or /private/tmp/ (macOS canonical path)
if [[ "$DIR" != /tmp/* && "$DIR" != /private/tmp/* ]]; then
    echo "ERROR: --dir must be under /tmp/ (got: $DIR)" >&2
    exit 1
fi

AUDIT_LOG="${TMPDIR:-/tmp}/larch-cleanup-audit.log"
AUDIT_TS=$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || echo "?")
AUDIT_PARENT=$(ps -o comm= -p "$PPID" 2>/dev/null | tr -d '\n' || true)
AUDIT_PARENT="${AUDIT_PARENT//[[:space:]]/_}"
: "${AUDIT_PARENT:=?}"
{ printf '%s pid=%s ppid=%s parent=%s dir=%s\n' "$AUDIT_TS" "$$" "$PPID" "$AUDIT_PARENT" "$DIR" >> "$AUDIT_LOG" && chmod 0644 "$AUDIT_LOG" 2>/dev/null; } 2>/dev/null || true

rm -rf "$DIR"
