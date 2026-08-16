#!/usr/bin/env bash
# Fixture: --help prints usage to stdout only (for validate-plan-commands harness).
set -euo pipefail
if [[ "${1:-}" == "--help" ]]; then
    printf '%s\n' 'Usage: demo-stdout-help.sh [--known-flag ARG]'
    exit 0
fi
exit 0
