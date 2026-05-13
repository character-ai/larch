#!/usr/bin/env bash
# detect-wholesale-rejection.sh — Detect all-findings-rejected early termination.

set -euo pipefail

usage() { echo "Usage: detect-wholesale-rejection.sh --accepted-count N" >&2; }

ACCEPTED_COUNT=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --accepted-count) ACCEPTED_COUNT="${2:?--accepted-count requires a value}"; shift 2 ;;
        --help) usage; exit 0 ;;
        *) echo "detect-wholesale-rejection.sh: unknown option: $1" >&2; usage; exit 2 ;;
    esac
done

case "$ACCEPTED_COUNT" in ''|*[!0-9]*) echo "detect-wholesale-rejection.sh: --accepted-count must be a non-negative integer" >&2; exit 2 ;; esac
if [[ "$ACCEPTED_COUNT" -eq 0 ]]; then
    printf 'TERMINATE_EARLY=true\n'
else
    printf 'TERMINATE_EARLY=false\n'
fi
