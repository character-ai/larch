#!/usr/bin/env bash
# read-session-env-key.sh — read one KEY=VALUE pair from a session-env file.
#
# Safe-parsing wrapper used by /implement Step 2.1 (and any other safe-parsing
# site) to extract a specific key from $IMPLEMENT_TMPDIR/session-env.sh without
# sourcing it. Matches the whole `KEY=` prefix on a line and emits everything
# after the first `=`, parallel to `value="${line#*=}"` in session-setup.sh.
# Deliberately avoids the legacy `awk -F= '$1=="KEY"{print $2; exit}' FILE`
# form because that truncates values containing additional `=` characters at
# the first separator. Sourcing is unsafe because the file's contents
# originate from environment probes; awk-based extraction prevents code
# execution from a hostile value.
#
# Usage:
#   read-session-env-key.sh --file PATH --key KEY [--default VALUE]
#
# Output:
#   On success: the resolved value on stdout (one line, no KEY= prefix).
#   When the key is missing OR has an empty value AND --default is set, the
#   default value is emitted; when the key is missing AND --default is
#   absent, nothing is emitted (caller distinguishes by capturing stdout
#   and applying its own fallback).
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

if [ -z "$FILE" ]; then
    # Empty --file is treated identically to an unreadable file below: when
    # --default is set, emit the default and exit 0; otherwise keep the
    # usage error. This lets standalone /design and /review (where
    # SESSION_ENV_PATH is intentionally empty) call this script in their
    # token-ledger rehydration blocks without emitting stderr noise or
    # tripping `set -e` in callers (#1563 round-2 review).
    if [ "$DEFAULT_SET" = "true" ]; then
        printf '%s\n' "$DEFAULT"
        exit 0
    fi
    echo "read-session-env-key.sh: --file is required" >&2
    exit 1
fi
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
# Print the substring after the first `=` so values containing additional `=`
# characters are not truncated (parallels session-setup.sh's `value="${line#*=}"`).
VALUE=$(awk -v k="$KEY" 'BEGIN{kl=length(k)} substr($0,1,kl)==k && substr($0,kl+1,1)=="=" {print substr($0,kl+2); exit}' "$FILE")

if [ -z "$VALUE" ] && [ "$DEFAULT_SET" = "true" ]; then
    printf '%s\n' "$DEFAULT"
else
    printf '%s\n' "$VALUE"
fi
