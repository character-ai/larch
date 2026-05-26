#!/usr/bin/env bash
# test-render-cost-line-callsites.sh — render-cost-line.sh is standalone-only post #2714.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd -P)"
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
pass() { printf 'PASS: %s\n' "$1"; }

if git -C "$REPO" grep -rln 'render-cost-line\.sh' -- skills >/dev/null 2>&1; then
    git -C "$REPO" grep -rln 'render-cost-line\.sh' -- skills >&2 || true
    fail 'skills/** must not reference render-cost-line.sh'
fi
pass 'zero render-cost-line references under skills/'

allowed_re='^(scripts/render-cost-line\.sh|scripts/render-cost-line\.md|scripts/test-render-cost-line\.sh|scripts/test-render-cost-line\.md|scripts/test-render-cost-line-callsites\.sh|scripts/test-render-cost-line-callsites\.md|scripts/test-render-cost-line-realism\.sh|scripts/test-render-cost-line-realism\.md|scripts/test-design-structure\.sh|scripts/test-token-vendor-scrapers\.sh|scripts/test-token-vendor-scrapers\.md)$'
while IFS= read -r rel; do
    [[ -n "$rel" ]] || continue
    if ! printf '%s\n' "$rel" | grep -Eq "$allowed_re"; then
        fail "unexpected render-cost-line.sh reference in $rel"
    fi
done < <(git -C "$REPO" grep -rln 'render-cost-line\.sh' -- scripts 2>/dev/null || true)
pass 'scripts/ render-cost-line references are allowlist-only'

if grep -Fq '💰 Cost:' "$REPO/scripts/token-report.sh"; then
    fail 'token-report.sh must not contain 💰 Cost: literal (summary/markdown paths)'
fi
pass 'token-report.sh has no 💰 Cost: literal'

f="$REPO/skills/design/scripts/render-final-summary.sh"
grep -Fq 'render-run-summary.sh' "$f" || fail 'render-final-summary.sh must invoke render-run-summary.sh'
b=$(grep -cF -- '--claude-input-tokens' "$f") || b=0
test "$b" -ge 1 || fail 'render-final-summary.sh must pass --claude-input-tokens to render-run-summary'
pass 'render-final-summary per-bucket argv shape'

printf 'PASS: test-render-cost-line-callsites.sh\n'
