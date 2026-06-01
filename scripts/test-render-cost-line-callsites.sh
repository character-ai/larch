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
grep -Fq 'if [ -s "$IMPLEMENT_TMPDIR/summary-final.md" ]; then' "$REPO/skills/implement/SKILL.md" || fail 'Step 17 must gate touch on non-empty summary body'
# shellcheck disable=SC2016
grep -Fq 'step-18b-final-report.sh" --implement-tmpdir "$IMPLEMENT_TMPDIR"' "$REPO/skills/implement/SKILL.md" || fail 'Step 18 must invoke step-18b-final-report.sh'
# shellcheck disable=SC2016
grep -Fq 'When `EMIT_BODY=true` and `WFR_RC=0` and `[ -s "$IMPLEMENT_TMPDIR/summary-final.md" ]`' "$REPO/skills/implement/SKILL.md" || fail 'Step 18 orchestrator emit must key on EMIT_BODY=true with WFR_RC=0 and non-empty summary-final.md'
# shellcheck disable=SC2016
grep -Fq 'write `$IMPLEMENT_TMPDIR/.step17-emitted`' "$REPO/skills/implement/SKILL.md" || fail 'Step 17/18 must persist top-chat emission sentinel'
# shellcheck disable=SC2016
step18_block=$(sed -n '/step-18b-final-report\.sh.*--implement-tmpdir "\$IMPLEMENT_TMPDIR"/,/^```$/p' "$REPO/skills/implement/SKILL.md")
# shellcheck disable=SC2016
if printf '%s\n' "$step18_block" | grep -Fq 'touch "$IMPLEMENT_TMPDIR/.step17-emitted"'; then
    fail 'Step 18 Bash block must not touch .step17-emitted before orchestrator emit'
fi
# shellcheck disable=SC2016
grep -Fq 'the orchestrator MUST emit the full body of summary-final.md verbatim as plain chat markdown' "$REPO/skills/implement/SKILL.md" || fail 'implement SKILL must pin Step 17 full-body emit prose'
# shellcheck disable=SC2016
grep -Fq 'When `EMIT_BODY=true` and `WFR_RC=0` and `[ -s "$IMPLEMENT_TMPDIR/summary-final.md" ]`, the orchestrator MUST emit the full body of summary-final.md verbatim as plain chat markdown' "$REPO/skills/implement/SKILL.md" || fail 'implement SKILL must pin Step 18 full-body emit prose keyed on EMIT_BODY'
# shellcheck disable=SC2016
grep -Fq 'The only orchestrator-text addition permitted after the Bash summary is the verbatim full-body emission of $IMPLEMENT_TMPDIR/summary-final.md' "$REPO/skills/implement/SKILL.md" || fail 'implement SKILL must pin NEVER #20 full-body exception prose'
grep -Fq 'NEVER write a free-form natural-language recap summary at end of turn after Step 17' "$REPO/skills/implement/SKILL.md" || fail 'implement SKILL must pin NEVER #20 literal'
grep -Fq 'SUMMARY_MODE_STRING=N/A' "$REPO/skills/design/SKILL.md" || fail 'design SKILL must default SUMMARY_MODE_STRING to N/A'
grep -Fq -- '--post-publish-only' "$REPO/skills/design/SKILL.md" || fail 'design SKILL must call render-final-summary.sh with --post-publish-only'
# shellcheck disable=SC2016
grep -Fq 'emit its full body verbatim as plain chat markdown' "$REPO/skills/design/SKILL.md" || fail 'design SKILL must pin post-publish full-body emit prose'
# shellcheck disable=SC2016
grep -Fq 'Step 5c `design-publish.sh` returns (`_publish_rc` 0, 1, or 3)' "$REPO/skills/design/SKILL.md" || fail 'design SKILL must pin post-driver full-body emit gate'
# shellcheck disable=SC2016
grep -Fq 'when `[ -s "${FINAL_SUMMARY_PATH:-$DESIGN_TMPDIR/final-summary.md}" ]`' "$REPO/skills/design/SKILL.md" || fail 'design SKILL must pin non-empty FINAL_SUMMARY_PATH emit gate'
# shellcheck disable=SC2016
grep -Fq 'Regardless of `PLAN_WRITE_OK`' "$REPO/skills/design/SKILL.md" || fail 'design SKILL must pin full-body emit regardless of PLAN_WRITE_OK'
# shellcheck disable=SC2016
grep -Fq 'when `$DESIGN_TMPDIR/final-summary.md` or parsed `FINAL_SUMMARY_PATH` is non-empty after driver handoff' "$REPO/skills/design/SKILL.md" || fail 'design SKILL must pin Step 5d post-driver final-summary gate'
grep -Fq 'NEVER write a free-form natural-language recap summary at end of turn' "$REPO/skills/design/SKILL.md" || fail 'design SKILL must pin anti-recap prose'
if grep -Fq 'gated on helper exit 0' "$REPO/skills/design/SKILL.md"; then
    fail 'design SKILL must not gate final-summary emit on helper exit 0'
fi
pass 'SKILL.md full-body summary callsite contracts pinned'

# shellcheck disable=SC2016
retired_prose=(
  'emit exactly that one line'
  'emit that single verbatim'
  'single extracted `- **Cost**:`'
  'The cost line is the sole exception'
  'orchestrator emits the single verbatim cost line'
  'single verbatim cost-line emit'
)
for retired in "${retired_prose[@]}"; do
  if git -C "$REPO" grep -Fq -- "$retired" skills/design/SKILL.md skills/implement/SKILL.md; then
    fail "retired cost-line-only prose remains: $retired"
  fi
done
pass 'retired cost-line-only prose absent from SKILL.md'

printf 'PASS: test-render-cost-line-callsites.sh\n'
