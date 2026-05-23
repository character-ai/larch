#!/usr/bin/env bash
# test-report-tokens-recompute.sh — /report-tokens shows reported vs estimated columns (DE-2622).
set -euo pipefail
REPO="$(cd "$(dirname "$0")/../../.." && pwd -P)"
FIX_SRC="$REPO/skills/report-tokens/scripts/fixtures/recompute-run"
RUN_DIR="$REPO/larch-logs/implement/AAAA-report-tokens-recompute-fixture"
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
pass() { printf 'PASS: %s\n' "$1"; }

# Avoid inheriting a parent Claude quiet-session FD contract (this harness runs under CI / tools).
unset LARCH_QUIET_ACTIVE LARCH_QUIET_PID LARCH_QUIET_LOG_FILE LARCH_QUIET_LOG \
    LARCH_QUIET_BREADCRUMBS LARCH_QUIET_BREADCRUMB_FD LARCH_QUIET_DISABLE 2>/dev/null || true

export LARCH_REPORT_TOKENS_REPO="${LARCH_REPORT_TOKENS_REPO:-fixture/local}"

cleanup() { rm -rf "$RUN_DIR"; }
trap cleanup EXIT
rm -rf "$RUN_DIR"
mkdir -p "$RUN_DIR"
cp "$FIX_SRC/manifest.json" "$FIX_SRC/token-report.json" "$RUN_DIR/"

export CLAUDE_PLUGIN_ROOT="$REPO"
export LARCH_REPORT_TOKENS_NO_ISSUE=1
export LARCH_REPORT_TOKENS_NO_PLOT=1
export LARCH_REPORT_TOKENS_LIMIT=500

out=$("$REPO/skills/report-tokens/scripts/run-analysis.sh")

case "$out" in
    *'### Reported vs estimated'*) ;;
    *) fail "analysis output missing reported vs estimated section";;
esac
case "$out" in
    *'#999001'*) ;;
    *) fail "fixture issue #999001 not listed";;
esac
case "$out" in
    *'token-cost.sh'*) ;;
    *) fail "summary line should mention token-cost.sh";;
esac
pass 'fixture run surfaced in reported vs estimated table'

printf 'PASS: test-report-tokens-recompute.sh\n'
