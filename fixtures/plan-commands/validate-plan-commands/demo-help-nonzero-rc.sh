#!/usr/bin/env bash
# Fixture: --help prints usage then exits non-zero; Tier 2 must still run flag checks.
set -euo pipefail
if [[ "${1:-}" == "--help" ]]; then
    printf '%s\n' 'Usage: demo-help-nonzero-rc.sh' '  --bad-flag   optional bad flag'
    exit 2
fi
exit 0
