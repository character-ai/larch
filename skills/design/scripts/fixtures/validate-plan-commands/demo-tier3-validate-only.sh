#!/usr/bin/env bash
# Fixture: Tier 3 registry hook --validate-only (no LARCH_DRY_RUN=1).
set -euo pipefail
if [[ "${1:-}" == "--help" ]]; then
    printf '%s\n' 'Usage: demo-tier3-validate-only.sh [--dry-flag ARG] [--validate-only]'
    exit 0
fi
for arg in "$@"; do
    if [[ "$arg" == "--validate-only" ]]; then
        exit 0
    fi
done
exit 1
