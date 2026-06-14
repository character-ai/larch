#!/usr/bin/env bash
# test-render-run-summary-callsites.sh — write-final-report pins render run-summary wiring.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd -P)"
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
pass() { printf 'PASS: %s\n' "$1"; }

f="$REPO/python/pr_body.py"
grep -Fq 'render_run_summary(' "$f" || fail "expected render_run_summary usage in pr_body.py"
grep -Fq '_final_report_token_fields' "$f" || fail "expected token/cost forwarding in pr_body.py"
grep -Fq 'emergency_requested' "$f" || fail "expected emergency_requested forwarding in pr_body.py"
pass 'write-final-report render_run_summary wiring'

g="$REPO/skills/design/scripts/render-final-summary.sh"
grep -Fq 'render run-summary' "$g" || fail "expected python/cli.py render run-summary invocation in render-final-summary.sh"
b2=$(grep -cF -- '--claude-input-tokens' "$g") || b2=0
test "$b2" -ge 1 || fail 'render-final-summary.sh must pass --claude-input-tokens'
pass 'render-final-summary render-run-summary per-bucket wiring'

printf 'PASS: test-render-run-summary-callsites.sh\n'
