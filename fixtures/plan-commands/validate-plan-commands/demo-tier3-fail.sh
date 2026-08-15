#!/usr/bin/env bash
# Fixture: Tier 3 dry-run failure under LARCH_DRY_RUN=1.
set -euo pipefail
if [[ "${1:-}" == "--help" ]]; then
    printf '%s\n' 'Usage: demo-tier3-fail.sh [--dry-flag ARG]'
    exit 0
fi
if [[ "${LARCH_DRY_RUN:-}" == "1" ]]; then
    exit 1
fi
exit 0
