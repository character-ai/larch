#!/usr/bin/env bash
# audit-pacific-timestamp.sh — Portable Pacific timestamp with PDT/PST detection.
#
# Output KV (stdout):
#   PACIFIC_TIMESTAMP=2026-05-20T21:59-07:00
#
# PDT (UTC-7): Mar second Sunday through Nov first Sunday
# PST (UTC-8): all other dates
#
# Exit codes: success prints KV on stdout and exits 0. Unexpected argv exits 1
# with stderr only — no PACIFIC_TIMESTAMP= line on stdout.

set -euo pipefail

if [ "$#" -gt 0 ]; then
    printf 'audit-pacific-timestamp.sh: unexpected argument(s)\n' >&2
    exit 1
fi

# Try TZ-based approach first (most reliable)
get_pacific_via_tz() {
    local ts
    # GNU date with TZ
        ts=$(TZ="America/Los_Angeles" date +"%Y-%m-%dT%H:%M%z" 2>/dev/null || true)
    if [ -n "$ts" ]; then
        # Convert +HHMM or -HHMM to +HH:MM / -HH:MM (also tolerate trailing Z from odd hosts)
        printf '%s' "$ts" | sed -E 's/([+-][0-9]{2})([0-9]{2})$/\1:\2/'
        return 0
    fi
    return 1
}

TS=""
PACIFIC_SOURCE="utc_fallback"
if TS=$(get_pacific_via_tz 2>/dev/null); then
    PACIFIC_SOURCE="tz_america_los_angeles"
else
    # No fake "Pacific" without TZ data — UTC minute-precision (see PACIFIC_TIMESTAMP_SOURCE).
    TS=$(date -u +"%Y-%m-%dT%H:%MZ" 2>/dev/null || date +"%Y-%m-%dT%H:%MZ")
fi

if [ -z "$TS" ]; then
    TS=$(date -u +"%Y-%m-%dT%H:%MZ" 2>/dev/null || date +"%Y-%m-%dT%H:%MZ")
fi

# Require minute precision with explicit offset or Z (reject mis-shaped "Pacific" labels)
if ! printf '%s' "$TS" | grep -qE '^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}([+-][0-9]{2}:[0-9]{2}|Z)$'; then
    TS=$(date -u +"%Y-%m-%dT%H:%MZ" 2>/dev/null || date +"%Y-%m-%dT%H:%MZ")
    PACIFIC_SOURCE="utc_fallback"
fi

printf 'PACIFIC_TIMESTAMP=%s\n' "$TS"
printf 'PACIFIC_TIMESTAMP_SOURCE=%s\n' "$PACIFIC_SOURCE"
