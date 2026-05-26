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

# shellcheck disable=SC2016
grep -Fq 'write-final-report.sh" --implement-tmpdir "$IMPLEMENT_TMPDIR" --print-stdout; then' "$REPO/skills/implement/SKILL.md" || fail 'Step 17 must gate touch on write-final-report success'
# shellcheck disable=SC2016
grep -Fq 'if grep -Fq -- '\''- **Cost**:'\'' "$IMPLEMENT_TMPDIR/summary-final.md" 2>/dev/null; then' "$REPO/skills/implement/SKILL.md" || fail 'Step 17 must gate touch on cost line presence'
grep -Fq '_wfr_args+=(--print-stdout)' "$REPO/skills/implement/SKILL.md" || fail 'Step 18 must only request --print-stdout when .step17-printed is absent'
# shellcheck disable=SC2016
grep -Fq 'if [ "$_wfr_printed" = true ] && grep -Fq -- '\''- **Cost**:'\'' "$IMPLEMENT_TMPDIR/summary-final.md" 2>/dev/null; then' "$REPO/skills/implement/SKILL.md" || fail 'Step 18 must gate .step17-printed on success plus cost line presence'
# shellcheck disable=SC2016
grep -Fq 'Immediately after the Step 17 Bash block returns, if the script succeeded and `summary-final.md` contains a line beginning with `- **Cost**:`' "$REPO/skills/implement/SKILL.md" || fail 'implement SKILL must pin Step 17 verbatim cost-line emit prose'
grep -Fq 'The cost line is the sole exception under NEVER #20.' "$REPO/skills/implement/SKILL.md" || fail 'implement SKILL must pin NEVER #20 cost-line exception prose'
grep -Fq 'NEVER write a free-form natural-language recap summary at end of turn after Step 17' "$REPO/skills/implement/SKILL.md" || fail 'implement SKILL must pin NEVER #20 literal'
grep -Fq 'SUMMARY_MODE_STRING=N/A' "$REPO/skills/design/SKILL.md" || fail 'design SKILL must default SUMMARY_MODE_STRING to N/A'
grep -Fq -- '--post-publish-only' "$REPO/skills/design/SKILL.md" || fail 'design SKILL must call render-final-summary.sh with --post-publish-only'
# shellcheck disable=SC2016
grep -Fq 'After every `render-final-summary.sh --post-publish-only` invocation in `/design`' "$REPO/skills/design/SKILL.md" || fail 'design SKILL must pin post-publish cost-line emit prose'
grep -Fq 'NEVER write a free-form natural-language recap summary at end of turn' "$REPO/skills/design/SKILL.md" || fail 'design SKILL must pin anti-recap prose'
pass 'SKILL.md cost-line callsite contracts pinned'

printf 'PASS: test-render-cost-line-callsites.sh\n'
