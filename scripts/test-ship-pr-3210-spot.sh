#!/usr/bin/env bash
# Spot-check #3210 fix-loop additions only.
set -euo pipefail
export LARCH_QUIET_DISABLE=1
unset LARCH_QUIET_BREADCRUMB_FD LARCH_QUIET_LOG_FILE
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
TMP_BASE="$(mktemp -d -t ship-pr-3210-spot.XXXXXX)"
PASS_COUNT=0 FAIL_COUNT=0
trap 'rm -rf "$TMP_BASE"' EXIT
# shellcheck source=scripts/test-ship-pr.sh
source "$REPO_ROOT/scripts/test-ship-pr.sh" --section __none__
