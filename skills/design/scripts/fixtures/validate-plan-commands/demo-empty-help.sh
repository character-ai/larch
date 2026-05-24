#!/usr/bin/env bash
# Fixture: --help exits 0 with empty stdout → Tier 2 SKIPPED_FLAG_CHECK (no-help path).
set -euo pipefail
if [[ "${1:-}" == "--help" ]]; then
    exit 0
fi
exit 0
