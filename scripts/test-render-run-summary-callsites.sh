#!/usr/bin/env bash
# test-render-run-summary-callsites.sh — write-final-report passes per-bucket flags (DE-2622).
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd -P)"
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
pass() { printf 'PASS: %s\n' "$1"; }

f="$REPO/skills/implement/scripts/write-final-report.sh"
c=$(grep -c 'render-run-summary\.sh' "$f") || c=0
test "$c" -ge 1 || fail "expected render-run-summary.sh invocations in write-final-report.sh"
b=$(grep -cF -- '--claude-input-tokens' "$f") || b=0
test "$b" -ge "$c" || fail "each render-run-summary invocation should pass --claude-input-tokens (blocks=$c flags=$b)"
pass 'write-final-report render-run-summary per-bucket wiring'

g="$REPO/skills/design/scripts/render-final-summary.sh"
grep -Fq 'render-run-summary.sh' "$g" || fail "expected render-run-summary.sh invocation in render-final-summary.sh"
b2=$(grep -cF -- '--claude-input-tokens' "$g") || b2=0
test "$b2" -ge 1 || fail 'render-final-summary.sh must pass --claude-input-tokens'
pass 'render-final-summary render-run-summary per-bucket wiring'

printf 'PASS: test-render-run-summary-callsites.sh\n'
