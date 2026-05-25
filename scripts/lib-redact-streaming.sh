#!/usr/bin/env bash
# lib-redact-streaming.sh — line-oriented wrapper around redact-secrets.sh --streaming.
#
# Usage: lib-redact-streaming.sh --state-file PATH < input > output
# Each input line is redacted with PEM state persisted in PATH across calls.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATE_FILE=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --state-file=*)
            STATE_FILE="${1#--state-file=}"
            shift
            ;;
        --state-file)
            STATE_FILE="${2:?}"
            shift 2
            ;;
        -h|--help)
            printf 'Usage: %s --state-file PATH < stdin > stdout\n' "$(basename "$0")" >&2
            exit 0
            ;;
        *)
            printf '%s: unknown option: %s\n' "$(basename "$0")" "$1" >&2
            exit 2
            ;;
    esac
done

[[ -n "$STATE_FILE" ]] || {
    printf '%s: --state-file is required\n' "$(basename "$0")" >&2
    exit 2
}

while IFS= read -r __lstream_line || [[ -n "${__lstream_line:-}" ]]; do
    if ! printf '%s\n' "$__lstream_line" | "$SCRIPT_DIR/redact-secrets.sh" --streaming --state-file="$STATE_FILE"; then
        exit 1
    fi
done
