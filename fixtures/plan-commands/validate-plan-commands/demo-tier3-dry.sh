#!/usr/bin/env bash
# Fixture: Tier 3 dry-run success under LARCH_DRY_RUN=1.
set -euo pipefail
if [[ "${1:-}" == "--help" ]]; then
    printf '%s\n' 'Usage: demo-tier3-dry.sh [--dry-flag ARG]'
    exit 0
fi
if [[ "${LARCH_DRY_RUN:-}" == "1" ]]; then
    exit 0
fi
exit 0
