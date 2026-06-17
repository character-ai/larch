#!/usr/bin/env bash
# test-render-cost-line-callsites.sh — python3 python/cli.py token render-cost-line is standalone-only post #2714.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd -P)"
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
pass() { printf 'PASS: %s\n' "$1"; }

if git -C "$REPO" grep -rln 'render-cost-line\.sh' -- skills >/dev/null 2>&1; then
    git -C "$REPO" grep -rln 'render-cost-line\.sh' -- skills >&2 || true
    fail 'skills/** must not reference python3 python/cli.py token render-cost-line'
fi
pass 'zero render-cost-line references under skills/'

allowed_re='^(scripts/render-cost-line\.sh|scripts/render-cost-line\.md|scripts/test-render-cost-line\.sh|scripts/test-render-cost-line\.md|scripts/test-render-cost-line-callsites\.sh|scripts/test-render-cost-line-callsites\.md|scripts/test-render-cost-line-realism\.sh|scripts/test-render-cost-line-realism\.md|scripts/test-design-structure\.sh|scripts/test-token-vendor-scrapers\.sh|scripts/test-token-vendor-scrapers\.md)$'
while IFS= read -r rel; do
    [[ -n "$rel" ]] || continue
    if ! printf '%s\n' "$rel" | grep -Eq "$allowed_re"; then
        fail "unexpected python3 python/cli.py token render-cost-line reference in $rel"
    fi
done < <(git -C "$REPO" grep -rln 'render-cost-line\.sh' -- scripts 2>/dev/null || true)
pass 'scripts/ render-cost-line references are allowlist-only'

if grep -Fq '💰 Cost:' "$REPO/python/tokens.py"; then
    fail 'python3 python/cli.py token report must not contain 💰 Cost: literal (summary/markdown paths)'
fi
pass 'token report implementation has no 💰 Cost: literal'

f="$REPO/python/design_summary.py"
grep -Fq 'render run-summary' "$f" || fail 'design_summary.py must invoke python/cli.py render run-summary'
b=$(grep -cF -- 'claude-input-tokens' "$f") || b=0
test "$b" -ge 1 || fail 'design_summary.py must pass --claude-input-tokens to render-run-summary'
pass 'design_summary.py render-run-summary per-bucket argv shape'

# Step 17 marker handoff lives in the composed Step 16-17 wrapper.
# shellcheck disable=SC2016
grep -Fq '"$SCRIPT_DIR/step-17.sh" --no-print-stdout || STEP17_RC=$?' "$REPO/skills/implement/scripts/step-16-17.sh" || fail 'Step 16-17 wrapper must call step-17.sh --no-print-stdout and capture rc'
# shellcheck disable=SC2016
grep -Fq 'STEP17_RC=0' "$REPO/skills/implement/scripts/step-16-17.sh" || fail 'Step 16-17 wrapper must initialize Step 17 rc before capture'
# shellcheck disable=SC2016
grep -Fq 'if [ "$STEP17_RC" -eq 0 ] && [ -s "$IMPLEMENT_TMPDIR/summary-final.md" ]; then' "$REPO/skills/implement/scripts/step-16-17.sh" || fail 'Step 16-17 wrapper must gate markers on Step 17 success and non-empty summary'
grep -Fq -- '---LARCH-SUMMARY-FINAL-BEGIN---' "$REPO/skills/implement/scripts/step-16-17.sh" || fail 'Step 16-17 wrapper must emit begin marker'
grep -Fq -- '---LARCH-SUMMARY-FINAL-END---' "$REPO/skills/implement/scripts/step-16-17.sh" || fail 'Step 16-17 wrapper must emit end marker'
# shellcheck disable=SC2016
grep -Fq 'final-report write --implement-tmpdir "$IMPLEMENT_TMPDIR" >"$_step17_wfr_log" 2>&1' "$REPO/skills/implement/scripts/step-17.sh" || fail 'Step 17 --no-print-stdout path must call final-report write without --print-stdout'
# shellcheck disable=SC2016
grep -Fq 'final-report write --implement-tmpdir "$IMPLEMENT_TMPDIR" --print-stdout >"$_step17_wfr_log" 2>&1' "$REPO/skills/implement/scripts/step-17.sh" || fail 'Step 17 default mode may retain --print-stdout'
grep -Fq -- '--category "Tool Failures"' "$REPO/skills/implement/scripts/step-17.sh" || fail 'Step 17 failure path must retain Tool Failures append'
# shellcheck disable=SC2016
step18_launcher='bash "$IMPLEMENT_TMPDIR/larch-run.sh" skills/implement/scripts/step-18.sh --phase finalize --step17-emitted "${STEP17_EMITTED_FOR_STEP18:-false}"'
# shellcheck disable=SC2016
grep -Fq "$step18_launcher" "$REPO/skills/implement/SKILL.md" || fail 'Step 18 must invoke step-18.sh finalize phase'
# shellcheck disable=SC2016
grep -Fq 'extract the first balanced whole-line `---LARCH-SUMMARY-FINAL-BEGIN---` / `---LARCH-SUMMARY-FINAL-END---` pair from captured wrapper output' "$REPO/skills/implement/SKILL.md" || fail 'implement SKILL must pin Step 17 marker extraction'
# shellcheck disable=SC2016
grep -Fq 'emit the extracted body verbatim as plain chat markdown' "$REPO/skills/implement/SKILL.md" || fail 'implement SKILL must pin Step 17 marker body emission'
# shellcheck disable=SC2016
grep -Fq 'Extract the first balanced whole-line `---LARCH-SUMMARY-FINAL-BEGIN---` / `---LARCH-SUMMARY-FINAL-END---` pair from captured `step-18.sh --phase finalize` stdout.' "$REPO/skills/implement/SKILL.md" || fail 'Step 18 orchestrator emit must extract markers from finalize stdout'
grep -Fq '**⚠ Step 18: EMIT_BODY=true but marker pair missing from finalize stdout.**' "$REPO/skills/implement/SKILL.md" || fail 'Step 18 missing-marker warning must be pinned'
grep -Fq 'STEP17_EMITTED_FOR_STEP18' "$REPO/skills/implement/SKILL.md" || fail 'Step 18 finalize fence must bind STEP17_EMITTED_FOR_STEP18'
grep -Fq 'Relay teardown tail records verbatim from captured finalize stdout.' "$REPO/skills/implement/SKILL.md" || fail 'Step 18 teardown tail relay must be pinned'
# shellcheck disable=SC2016
grep -Fq 'write `$IMPLEMENT_TMPDIR/.step17-emitted`' "$REPO/skills/implement/SKILL.md" || fail 'Step 17/18 must persist top-chat emission sentinel'
# shellcheck disable=SC2016
step18_block=$(awk '
    /bash "\$IMPLEMENT_TMPDIR\/larch-run\.sh" skills\/implement\/scripts\/step-18\.sh --phase finalize/ { in_block=1 }
    in_block { print }
    in_block && /^```$/ { exit }
' "$REPO/skills/implement/SKILL.md")
# shellcheck disable=SC2016
if printf '%s\n' "$step18_block" | grep -Fq 'touch "$IMPLEMENT_TMPDIR/.step17-emitted"'; then
    fail 'Step 18 Bash block must not touch .step17-emitted before orchestrator emit'
fi
# shellcheck disable=SC2016
grep -Fq 'When a non-empty marker body is present, emit the extracted body verbatim as plain chat markdown.' "$REPO/skills/implement/SKILL.md" || fail 'implement SKILL must pin Step 17 full-body emit prose'
# shellcheck disable=SC2016
grep -Fq 'When marker extraction yields a non-empty body, emit that body verbatim as plain chat markdown.' "$REPO/skills/implement/SKILL.md" || fail 'implement SKILL must pin Step 18 marker body emit prose'
# shellcheck disable=SC2016
grep -Fq 'The only orchestrator-text addition permitted after the Bash summary is the verbatim full-body emission of the extracted marker body defined in Step 17 or the extracted marker body from captured `step-18.sh --phase finalize` stdout.' "$REPO/skills/implement/SKILL.md" || fail 'implement SKILL must pin NEVER #17 Step 18 marker exception prose'
grep -Fq 'NEVER write a free-form natural-language recap summary at end of turn after Step 17' "$REPO/skills/implement/SKILL.md" || fail 'implement SKILL must pin NEVER #20 literal'
grep -Fq -- '--post-publish-only' "$REPO/skills/design/SKILL.md" || fail 'design SKILL must call render-final-summary.sh with --post-publish-only'
# shellcheck disable=SC2016
grep -Fq 'emit its full body verbatim as plain chat markdown' "$REPO/skills/design/SKILL.md" || fail 'design SKILL must pin post-publish full-body emit prose'
# shellcheck disable=SC2016
grep -Fq 'Step 5c `python/cli.py design publish` returns with the latest `_publish_rc` 0, 1, or 3' "$REPO/skills/design/SKILL.md" || fail 'design SKILL must pin post-driver full-body emit gate with rc 4 carve-out'
# shellcheck disable=SC2016
grep -Fq 'when `[ -s "${FINAL_SUMMARY_PATH:-$DESIGN_TMPDIR/final-summary.md}" ]`' "$REPO/skills/design/SKILL.md" || fail 'design SKILL must pin non-empty FINAL_SUMMARY_PATH emit gate'
# shellcheck disable=SC2016
grep -Fq 'Regardless of `PLAN_WRITE_OK`' "$REPO/skills/design/SKILL.md" || fail 'design SKILL must pin full-body emit regardless of PLAN_WRITE_OK'
# shellcheck disable=SC2016
grep -Fq 'marker extraction after driver handoff (`_publish_rc` 0, 1, or 3), with a non-empty `$DESIGN_TMPDIR/final-summary.md` or parsed `FINAL_SUMMARY_PATH` Read fallback' "$REPO/skills/design/SKILL.md" || fail 'design SKILL must pin Step 5d marker-extraction post-driver final-summary gate'
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
