#!/usr/bin/env bash
# read-session-env-key.sh — read one KEY=VALUE pair from a session-env file.
#
# Wraps the inline `awk -F= '$1=="KEY"{print $2; exit}' FILE` pattern that
# /implement Step 2.1 (and any other safe-parsing site) uses to extract a
# specific key from $IMPLEMENT_TMPDIR/session-env.sh without sourcing it.
# Sourcing is unsafe because the file's contents originate from environment
# probes; awk-based extraction prevents code execution from a hostile value.
#
# Usage:
#   read-session-env-key.sh --file PATH --key KEY [--default VALUE]
#
# Output:
#   On success or when key is missing: the resolved value on stdout (one
#   line, no KEY= prefix). When the key is missing AND --default is set,
#   the default value is emitted; when the key is missing AND --default is
#   absent, nothing is emitted (caller distinguishes by capturing stdout
#   and applying its own fallback — matches the inline pattern's
#   `[[ -z "$x" ]] && x=false` post-check).
#
# Exit codes:
#   0 — success (value or default emitted, or empty when key missing and
#       no --default)
#   1 — usage error or unreadable file

set -euo pipefail

FILE=""
KEY=""
DEFAULT=""
DEFAULT_SET=false

while [ $# -gt 0 ]; do
    case "$1" in
        --file)
            [ $# -ge 2 ] || { echo "read-session-env-key.sh: --file requires a value" >&2; exit 1; }
            FILE="$2"; shift 2 ;;
        --key)
            [ $# -ge 2 ] || { echo "read-session-env-key.sh: --key requires a value" >&2; exit 1; }
            KEY="$2"; shift 2 ;;
        --default)
            [ $# -ge 2 ] || { echo "read-session-env-key.sh: --default requires a value" >&2; exit 1; }
            DEFAULT="$2"; DEFAULT_SET=true; shift 2 ;;
        *)
            echo "read-session-env-key.sh: unknown flag: $1" >&2; exit 1 ;;
    esac
done

[ -n "$FILE" ] || { echo "read-session-env-key.sh: --file is required" >&2; exit 1; }
[ -n "$KEY" ]  || { echo "read-session-env-key.sh: --key is required"  >&2; exit 1; }

if [ ! -r "$FILE" ]; then
    if [ "$DEFAULT_SET" = "true" ]; then
        printf '%s\n' "$DEFAULT"
        exit 0
    fi
    echo "read-session-env-key.sh: cannot read $FILE" >&2
    exit 1
fi

# Use awk for safe key-based extraction (no source / eval). First match wins.
VALUE=$(awk -F= -v k="$KEY" '$1==k{print $2; exit}' "$FILE")

if [ -z "$VALUE" ] && [ "$DEFAULT_SET" = "true" ]; then
    printf '%s\n' "$DEFAULT"
else
    printf '%s\n' "$VALUE"
fi
