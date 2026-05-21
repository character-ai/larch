#!/usr/bin/env bash
# JSON-escape for embedding in double-quoted JSON string segments (jq handles controls/unicode).
# Sourced by audit-scan-run.sh and test-audit-runs.sh so tests exercise the shipped implementation.

jstr() {
    local _j
    _j=$(jq -nj --arg s "$1" '$s | @json' 2>/dev/null) || _j=""
    if [ -z "$_j" ] || [ "${#_j}" -lt 2 ]; then
        printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g; s/\r/\\r/g; s/\n/\\n/g; s/\t/\\t/g' | LC_ALL=C tr -d '\000-\010\013\014\016-\037\177'
        return
    fi
    printf '%s' "${_j:1:${#_j}-2}"
}
