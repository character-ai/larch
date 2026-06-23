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

design_skill="$REPO/skills/design/SKILL.md"
shared_final_summary="$REPO/skills/shared/final-summary-emit.md"

# Step 17 marker handoff lives in python/closeout.py.
grep -Fq 'step_17(["--implement-tmpdir", str(tmpdir), "--no-print-stdout"])' "$REPO/python/closeout.py" || fail 'Step 16-17 wrapper must call Step 17 no-print path and capture rc'
grep -Fq 'step17_rc == 0 and _summary_nonempty(tmpdir)' "$REPO/python/closeout.py" || fail 'Step 16-17 wrapper must gate markers on Step 17 success and non-empty summary'
grep -Fq -- '---LARCH-SUMMARY-FINAL-BEGIN---' "$REPO/python/closeout.py" || fail 'Step 16-17 wrapper must emit begin marker'
grep -Fq -- '---LARCH-SUMMARY-FINAL-END---' "$REPO/python/closeout.py" || fail 'Step 16-17 wrapper must emit end marker'
grep -Fq '"final-report", "write", "--implement-tmpdir"' "$REPO/python/closeout.py" || fail 'Step 17 path must call final-report write'
grep -Fq '"--print-stdout"' "$REPO/python/closeout.py" || fail 'Step 17 default mode may retain --print-stdout'
grep -Fq 'category="Tool Failures"' "$REPO/python/closeout.py" || fail 'Step 17 failure path must retain Tool Failures append'
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
grep -Fq -- '--post-publish-only' "$design_skill" || fail 'design SKILL must call render-final-summary.sh with --post-publish-only'
# shellcheck disable=SC2016
grep -Fq 'emit its full body verbatim as plain chat markdown' "$shared_final_summary" || fail 'shared final-summary emit must pin full-body emit prose'
# shellcheck disable=SC2016
grep -Fq 'Locate the first balanced whole-line `LARCH_FINAL_SUMMARY_BEGIN` / `LARCH_FINAL_SUMMARY_END` pair in the completed task `<task-notification>` stdout already in the orchestrator context window.' "$shared_final_summary" || fail 'shared final-summary emit must pin in-context task-notification marker extraction'
# shellcheck disable=SC2016
grep -Fq 'Do NOT paraphrase, summarize, reorder, or add prose between bullets.' "$shared_final_summary" || fail 'shared final-summary emit must pin no-paraphrase prose'
# shellcheck disable=SC2016
grep -Fq 'When the completed notification stdout includes non-empty `REPORT_GATE_SIDECARS_FILE=<path>`, Read that file and emit its full body verbatim immediately after the final-summary body.' "$shared_final_summary" || fail 'shared final-summary emit must pin sidecar follow-on'
# shellcheck disable=SC2016
grep -Fq 'Do not re-read task-output files, stdout captures, result env files, or tmpdir logs to recover markers.' "$shared_final_summary" || fail 'shared final-summary emit must forbid task-output re-reads'
grep -Fq 'Do not scrape markers via Bash or Python.' "$shared_final_summary" || fail 'shared final-summary emit must forbid Bash/Python marker scraping'
# shellcheck disable=SC2016
grep -Fq 'use the Read tool on `${FINAL_SUMMARY_PATH:-$DESIGN_TMPDIR/final-summary.md}` when non-empty' "$shared_final_summary" || fail 'shared final-summary emit must pin non-empty Read fallback'
grep -Fq 'Skip marker extraction entirely; do not scan prior tool output for markers.' "$shared_final_summary" || fail 'shared final-summary emit must pin file-only no-marker behavior'

# shellcheck disable=SC2016
grep -Fq 'marker-first profile for completed Step 5c task output when `_publish_rc` is 0, 1, or 3' "$design_skill" || fail 'design SKILL must pin post-driver full-body emit gate with rc 4 carve-out'
# shellcheck disable=SC2016
grep -Fq 'when `[ -s "${FINAL_SUMMARY_PATH:-$DESIGN_TMPDIR/final-summary.md}" ]`' "$design_skill" || fail 'design SKILL must pin non-empty FINAL_SUMMARY_PATH emit gate'
# shellcheck disable=SC2016
grep -Fq 'follow the file-only profile in `${CLAUDE_PLUGIN_ROOT}/skills/shared/final-summary-emit.md`' "$design_skill" || fail 'design SKILL must pin Step 0b file-only profile'
# shellcheck disable=SC2016
grep -Fq 'Regardless of `PLAN_WRITE_OK`' "$design_skill" || fail 'design SKILL must pin full-body emit regardless of PLAN_WRITE_OK'
# shellcheck disable=SC2016
grep -Fq 'Step 5d post-driver gate: after `_publish_rc` 0, 1, or 3, Step 5c item 5 follows the marker-first profile in `${CLAUDE_PLUGIN_ROOT}/skills/shared/final-summary-emit.md`' "$design_skill" || fail 'design SKILL must pin Step 5d compact shared emit gate'
grep -Fq 'NEVER write a free-form natural-language recap summary at end of turn' "$design_skill" || fail 'design SKILL must pin anti-recap prose'
pointer_count=$(grep -cF 'skills/shared/final-summary-emit.md' "$design_skill") || pointer_count=0
test "$pointer_count" -ge 6 || fail 'design SKILL must point each final-summary emit site to shared final-summary emit contract'
if grep -Fq 'Primary path: locate the markers in the task notification output text already in your context window' "$design_skill"; then
    fail 'design SKILL must not retain full marker-extraction procedure prose'
fi
if grep -Fq 'Do NOT use a Bash tool call, Python script, or any other tool invocation to extract or print the final-summary body' "$design_skill"; then
    fail 'design SKILL must not retain full tool-call prohibition procedure prose'
fi
if grep -Fq 'Do NOT paraphrase, summarize, reorder, or add prose between bullets' "$design_skill"; then
    fail 'design SKILL must not retain shared no-paraphrase procedure prose'
fi
if grep -Fq 'gated on helper exit 0' "$design_skill"; then
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
