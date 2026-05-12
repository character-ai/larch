#!/usr/bin/env bash
# cleanup-tmpdir.sh — Safely remove a session temp directory.
#
# Validates that the path is non-empty and under a larch session tmp root
# before running rm -rf. This prevents accidental deletion of non-temp
# directories if the caller passes an empty or wrong path.
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

cache_sessions_root() {
    printf '%s/larch/sessions' "${XDG_CACHE_HOME:-${HOME:-/tmp}/.cache}"
}

is_allowed_tmpdir() {
    local dir=$1
    local cache_root
    cache_root=$(cache_sessions_root)
    case "$dir" in
        /tmp/*|/private/tmp/*|/var/folders/*|/private/var/folders/*) return 0 ;;
        "$cache_root"/*) return 0 ;;
        *) return 1 ;;
    esac
}

DIR=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --dir) DIR="${2:?--dir requires a value}"; shift 2 ;;
        --help) usage; exit 0 ;;
        -*) echo "Unknown option: $1" >&2; usage; exit 1 ;;
        *) DIR="$1"; shift ;;
    esac
done

if [[ -z "$DIR" ]]; then
    echo "ERROR: --dir is required and must be non-empty" >&2
    exit 1
fi

# Validate path is under an accepted larch temp root.
if ! is_allowed_tmpdir "$DIR"; then
    echo "ERROR: --dir must be under /tmp/, /private/tmp/, /var/folders/, or $(cache_sessions_root)/ (got: $DIR)" >&2
    exit 1
fi

AUDIT_LOG="${TMPDIR:-/tmp}/larch-cleanup-audit.log"
AUDIT_TS=$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || echo "?")
AUDIT_PARENT=$(ps -o comm= -p "$PPID" 2>/dev/null | tr -d '\n' || true)
AUDIT_PARENT="${AUDIT_PARENT//[[:space:]]/_}"
: "${AUDIT_PARENT:=?}"
{ printf '%s pid=%s ppid=%s parent=%s dir=%s\n' "$AUDIT_TS" "$$" "$PPID" "$AUDIT_PARENT" "$DIR" >> "$AUDIT_LOG"; } 2>/dev/null || true

rm -rf "$DIR"
