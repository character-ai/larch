#!/usr/bin/env bash
# Spot-check #3210 rebase/rebump + CI-fix vendor paths (subset of fix-loop).
# Scenarios live under scripts/test-ship-pr.sh --section fix-loop.
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec bash "$REPO_ROOT/scripts/test-ship-pr.sh" --section fix-loop
