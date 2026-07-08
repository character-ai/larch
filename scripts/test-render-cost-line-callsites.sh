#!/usr/bin/env bash
# test-render-cost-line-callsites.sh — python3 python/cli.py token render-cost-line is standalone-only post #2714.
# Literal contract pins intentionally use backticks inside single-quoted grep needles.
# shellcheck disable=SC2016
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

if grep -Fq '💰 Cost:' "$REPO/python/larch/report/tokens.py"; then
    fail 'python3 python/cli.py token report must not contain 💰 Cost: literal (summary/markdown paths)'
fi
pass 'token report implementation has no 💰 Cost: literal'

f="$REPO/python/larch/design/design_summary.py"
grep -Fq 'render run-summary' "$f" || fail 'design_summary.py must invoke python/cli.py render run-summary'
b=$(grep -cF -- 'claude-input-tokens' "$f") || b=0
test "$b" -ge 1 || fail 'design_summary.py must pass --claude-input-tokens to render-run-summary'
pass 'design_summary.py render-run-summary per-bucket argv shape'

design_skill="$REPO/skills/design/SKILL.md"
finalize_step5="$REPO/skills/design/references/finalize-step5.md"
shared_final_summary="$REPO/skills/shared/final-summary-emit.md"

# Step 17 marker handoff lives in python/larch/state/closeout.py.
grep -Fq 'step_17(["--implement-tmpdir", str(tmpdir), "--no-print-stdout"])' "$REPO/python/larch/state/closeout.py" || fail 'Step 16-17 wrapper must call Step 17 no-print path and capture rc'
grep -Fq 'step17_rc == 0 and _summary_nonempty(tmpdir)' "$REPO/python/larch/state/closeout.py" || fail 'Step 16-17 wrapper must gate markers on Step 17 success and non-empty summary'
grep -Fq -- '---LARCH-SUMMARY-FINAL-BEGIN---' "$REPO/python/larch/state/closeout.py" || fail 'Step 16-17 wrapper must emit begin marker'
grep -Fq -- '---LARCH-SUMMARY-FINAL-END---' "$REPO/python/larch/state/closeout.py" || fail 'Step 16-17 wrapper must emit end marker'
grep -Fq '"final-report", "write", "--implement-tmpdir"' "$REPO/python/larch/state/closeout.py" || fail 'Step 17 path must call final-report write'
grep -Fq '"--print-stdout"' "$REPO/python/larch/state/closeout.py" || fail 'Step 17 default mode may retain --print-stdout'
grep -Fq 'category="Tool Failures"' "$REPO/python/larch/state/closeout.py" || fail 'Step 17 failure path must retain Tool Failures append'
# shellcheck disable=SC2016
step18_launcher='"$HOME/.cache/larch/sessions/implement-run-$PPID.sh" skills/implement/scripts/step-18.sh --phase finalize --step17-emitted "${STEP17_EMITTED_FOR_STEP18:-false}"'
# shellcheck disable=SC2016
grep -Fq "$step18_launcher" "$REPO/skills/implement/SKILL.md" || fail 'Step 18 must invoke step-18.sh finalize phase'
# shellcheck disable=SC2016
step18_composite='"$HOME/.cache/larch/sessions/implement-run-$PPID.sh" python/cli.py implement step-18-gate-finalize --implement-tmpdir "$IMPLEMENT_TMPDIR" --stall-tracking-memory "${STALL_TRACKING:-false}" --step17-emitted "${STEP17_EMITTED_FOR_STEP18:-false}"'
# shellcheck disable=SC2016
grep -Fq "$step18_composite" "$REPO/skills/implement/SKILL.md" || fail 'Step 18 must invoke composite gate-finalize path'
# shellcheck disable=SC2016
grep -Fq 'skills/shared/final-summary-emit.md' "$REPO/skills/implement/SKILL.md" || fail 'implement SKILL must point to shared final-summary emit contract'
# shellcheck disable=SC2016
grep -Fq 'markers `---LARCH-SUMMARY-FINAL-BEGIN---` / `---LARCH-SUMMARY-FINAL-END---`' "$REPO/skills/implement/SKILL.md" || fail 'implement SKILL must bind implement marker pair'
# shellcheck disable=SC2016
grep -Fq 'captured foreground `python/cli.py implement step-16-17` Bash wrapper stdout' "$REPO/skills/implement/SKILL.md" || fail 'implement SKILL must bind Step 17 captured foreground stdout source'
# shellcheck disable=SC2016
grep -Fq 'captured foreground `python/cli.py implement step-18-gate-finalize` Bash wrapper stdout' "$REPO/skills/implement/SKILL.md" || fail 'implement SKILL must bind Step 18 composite stdout source'
# shellcheck disable=SC2016
grep -Fq 'captured foreground `step-18.sh --phase finalize` Bash wrapper stdout' "$REPO/skills/implement/SKILL.md" || fail 'implement SKILL must bind Step 18b captured foreground stdout source'
grep -Fq 'not `<task-notification>` output' "$REPO/skills/implement/SKILL.md" || fail 'implement SKILL must forbid task-notification as implement summary source'
grep -Fq 'Read fallback `forbidden`' "$REPO/skills/implement/SKILL.md" || fail 'implement SKILL must forbid Read fallback for Step 17/18b'
grep -Fq 'sidecar follow-on `forbidden`' "$REPO/skills/implement/SKILL.md" || fail 'implement SKILL must forbid sidecar follow-on for Step 17/18b'
grep -Fq '**⚠ Step 18: EMIT_BODY=true but marker pair missing from composite stdout.**' "$REPO/skills/implement/SKILL.md" || fail 'Step 18 composite missing-marker warning must be pinned'
grep -Fq '**⚠ Step 18: EMIT_BODY=true but marker pair missing from finalize stdout.**' "$REPO/skills/implement/SKILL.md" || fail 'Step 18 finalize missing-marker warning must be pinned'
grep -Fq 'STEP17_EMITTED_FOR_STEP18' "$REPO/skills/implement/SKILL.md" || fail 'Step 18 finalize fence must bind STEP17_EMITTED_FOR_STEP18'
grep -Fq 'Relay teardown tail records verbatim from captured composite stdout on `NEXT_ACTION=finalize-done`, or from captured finalize stdout on the stall-recovery path.' "$REPO/skills/implement/SKILL.md" || fail 'Step 18 teardown tail relay must be dual-source pinned'
# shellcheck disable=SC2016
grep -Fq 'write `$IMPLEMENT_TMPDIR/.step17-emitted`' "$REPO/skills/implement/SKILL.md" || fail 'Step 17/18 must persist top-chat emission sentinel'
# shellcheck disable=SC2016
step18_block=$(awk '
    /"\$HOME\/\.cache\/larch\/sessions\/implement-run-\$PPID\.sh" skills\/implement\/scripts\/step-18\.sh --phase finalize/ { in_block=1 }
    in_block { print }
    in_block && /^```$/ { exit }
' "$REPO/skills/implement/SKILL.md")
# shellcheck disable=SC2016
if printf '%s\n' "$step18_block" | grep -Fq 'touch "$IMPLEMENT_TMPDIR/.step17-emitted"'; then
    fail 'Step 18 Bash block must not touch .step17-emitted before orchestrator emit'
fi
# shellcheck disable=SC2016
grep -Fq 'When the shared profile caches a non-empty marker body, retain it as the Step 17 cache for deferred terminal emit.' "$REPO/skills/implement/SKILL.md" || fail 'implement SKILL must pin Step 17 deferred cache'
grep -Fq 'Use `true` only when a non-empty Step 17 marker body was cached for deferred terminal emit; otherwise use `false`.' "$REPO/skills/implement/SKILL.md" || fail 'implement SKILL must bind Step 18 sentinel to a cached body'
# shellcheck disable=SC2016
grep -Fq 'The only final orchestrator-text addition permitted is one verbatim full-body emission from the selected cached Step 18 or Step 17 source at terminal text position.' "$REPO/skills/implement/SKILL.md" || fail 'implement SKILL must pin NEVER #17 terminal exception prose'
grep -Fq 'terminal chat emit must use that post-Step-18b marker body even if a Step 17 cache exists' "$REPO/skills/implement/SKILL.md" || fail 'implement SKILL must pin Step 18-over-Step 17 precedence'
grep -Fq 'NEVER write a free-form natural-language recap summary at end of turn after Step 17' "$REPO/skills/implement/SKILL.md" || fail 'implement SKILL must pin NEVER #20 literal'
grep -Fq -- '--post-publish-only' "$design_skill" || fail 'design SKILL must call render-final-summary.sh with --post-publish-only'
# shellcheck disable=SC2016
grep -Fq 'emit its full body verbatim as plain chat markdown' "$shared_final_summary" || fail 'shared final-summary emit must pin full-body emit prose'
grep -Fq 'Caller profile parameters' "$shared_final_summary" || fail 'shared final-summary emit must define caller profile parameters'
grep -Fq 'caller begin/end marker pair' "$shared_final_summary" || fail 'shared final-summary emit must parameterize marker tokens'
grep -Fq 'source description: task-output, wrapper stdout, or bgjob `DONE` stdout plus result env' "$shared_final_summary" || fail 'shared final-summary emit must parameterize summary source'
grep -Fq 'caller-named source already in the orchestrator context window' "$shared_final_summary" || fail 'shared final-summary emit must parameterize marker source'
grep -Fq '`/implement` binds captured foreground Bash wrapper stdout, not `<task-notification>`.' "$shared_final_summary" || fail 'shared final-summary emit must distinguish implement source from task notifications'
# shellcheck disable=SC2016
grep -Fq 'Only when steps 1–2 yield no valid marker body and the caller Read fallback policy is `allowed`, Read/cache the caller-named fallback path when non-empty.' "$shared_final_summary" || fail 'shared final-summary emit must gate Read fallback on absent/invalid markers and caller policy'
grep -Fq 'Do not extract or emit summary bodies from marker pairs on `/design` paths.' "$shared_final_summary" || fail 'shared final-summary emit must forbid /design marker-body extraction'
grep -Fq 'When the caller Read fallback policy is `forbidden`, skip Read fallback entirely.' "$shared_final_summary" || fail 'shared final-summary emit must define forbidden Read fallback'
grep -Fq 'Only when the caller sidecar policy is `allowed`' "$shared_final_summary" || fail 'shared final-summary emit must gate sidecar follow-on on caller policy'
grep -Fq 'When the caller sidecar policy is `forbidden`, skip sidecar follow-on entirely.' "$shared_final_summary" || fail 'shared final-summary emit must define forbidden sidecar follow-on'
# shellcheck disable=SC2016
grep -Fq 'Do not re-read task-output files, stdout captures, unrelated result env files, or tmpdir logs to recover markers.' "$shared_final_summary" || fail 'shared final-summary emit must forbid unrelated task-output and result-env re-reads'
grep -Fq 'Do not scrape markers via Bash or Python.' "$shared_final_summary" || fail 'shared final-summary emit must forbid Bash/Python marker scraping'
grep -Fq '`/design` Read-always readiness' "$shared_final_summary" || fail 'shared final-summary emit must include design readiness callsite binding'
grep -Fq 'Use this profile for `/design` final `bgjob wait` `DONE` stdout and the matching bgjob result env.' "$shared_final_summary" || fail 'shared final-summary emit must bind design profile to bgjob DONE stdout and result env'
grep -Fq 'final `bgjob wait` `DONE` stdout plus matching `$DESIGN_TMPDIR/bgjob/<step>.result.env` after `BGJOB_RC=0` and required-KV validation' "$shared_final_summary" || fail 'shared final-summary emit must include design bgjob source binding'
grep -Fq '`/implement` Step 17 marker-first' "$shared_final_summary" || fail 'shared final-summary emit must include implement Step 17 callsite binding'
grep -Fq '`/implement` Step 18b marker-first' "$shared_final_summary" || fail 'shared final-summary emit must include implement Step 18b callsite binding'
grep -Fq 'green path: captured foreground `python/cli.py implement step-18-gate-finalize` Bash wrapper stdout when `NEXT_ACTION=finalize-done`' "$shared_final_summary" || fail 'shared final-summary emit must include composite green-path binding'
grep -Fq 'non-green path: captured foreground `step-18.sh --phase finalize` Bash wrapper stdout on stall-recovery and escalation-filing branches' "$shared_final_summary" || fail 'shared final-summary emit must include breakout finalize binding'
grep -Fq 'Skip marker extraction entirely; do not scan prior tool output for markers.' "$shared_final_summary" || fail 'shared final-summary emit must pin file-only no-marker behavior'

# shellcheck disable=SC2016
grep -Fq 'The `/design` Read-always readiness profile in `${CLAUDE_PLUGIN_ROOT}/skills/shared/final-summary-emit.md` reads/caches' "$design_skill" || fail 'design SKILL anti-halt must point to shared Read-always readiness profile'
grep -Fq 'when `_publish_rc` is 0, 1, or 3, including `_publish_rc`=1 after plan-block-write failure' "$design_skill" || fail 'design SKILL must pin post-driver full-body cache gate with rc 4 carve-out'
# shellcheck disable=SC2016
grep -Fq 'follow the file-only profile in `${CLAUDE_PLUGIN_ROOT}/skills/shared/final-summary-emit.md`' "$design_skill" || fail 'design SKILL must pin Step 0b file-only profile'
# shellcheck disable=SC2016
grep -Fq 'when `[ -s "${FINAL_SUMMARY_PATH:-$DESIGN_TMPDIR/final-summary.md}" ]`' "$design_skill" || fail 'design SKILL must pin non-empty FINAL_SUMMARY_PATH emit gate'
# shellcheck disable=SC2016
grep -Fq 'Regardless of `PLAN_WRITE_OK`' "$design_skill" || fail 'design SKILL must pin full-body Read/cache regardless of PLAN_WRITE_OK'
grep -Fq 'NEVER write a free-form natural-language recap summary at end of turn' "$design_skill" || fail 'design SKILL must pin anti-recap prose'
grep -Fq 'parenthetical cost paraphrase such as `~$10.46`' "$design_skill" || fail 'design SKILL must pin no-cost-paraphrase prose'
grep -Fq '**Not** gated on `python/cli.py design render-final-summary` exit 0' "$design_skill" || fail 'design SKILL must pin render-exit carve-out'
grep -Fq 'parse `FINAL_SUMMARY_PATH=<path>` from that completed stdout and follow the `/design` Read-always readiness profile' "$design_skill" || fail 'cancellation fence must cite shared readiness profile without full binding paragraph'
grep -Fq 'Parse `FINAL_SUMMARY_PATH=<path>` from final `bgjob wait` `DONE` stdout' "$finalize_step5" || fail 'Step 5c abort path must name bgjob DONE stdout source and cite shared readiness profile'
grep -Fq 'parse `FINAL_SUMMARY_PATH=<path>` from `$DESIGN_TMPDIR/bgjob/design-step5c.result.env` or final `DONE` stdout, follow the `/design` Read-always readiness profile' "$design_skill" || fail 'Step 5c abort must name bgjob result env source and cite shared readiness profile'
grep -Fq 'Step 5d post-driver gate: after `_publish_rc` 0, 1, or 3, Step 5c item 5 must follow the `/design` Read-always readiness profile' "$design_skill" || fail 'Step 5d must back-reference Step 5c item 5 shared readiness profile'
grep -Fq 'Complete the shared sidecar Read/cache before any cleanup, cancellation line, or exit.' "$design_skill" || fail 'cancellation fence must preserve sidecar Read/cache ordering'
grep -Fq 'follow the `/design` Read-always readiness profile to Read/cache the final summary and allowed sidecars before tmpdir loss' "$finalize_step5" || fail 'Step 5c abort must preserve sidecar Read/cache before tmpdir loss'
grep -Fq 'Apply terminal emit **after** the plan-write failure warning or success footer decisions below, and after Step 6 cleanup when cleanup runs.' "$design_skill" || fail 'Step 5c item 5 must preserve deferred terminal ordering'
grep -Fq 'No free-form recap may appear between or after terminal emission.' "$design_skill" || fail 'Step 5d must preserve no-recap terminal ordering token'
grep -Fq 'Do not add post-emit recap prose, artifact bullet recaps, or parenthetical cost paraphrases such as approximate no-cost restatements.' "$shared_final_summary" || fail 'shared final-summary emit must pin recap/no-cost rule'
render_exit_count=$(grep -cF '**Not** gated on `python/cli.py design render-final-summary` exit 0' "$design_skill") || render_exit_count=0
test "$render_exit_count" -ge 2 || fail 'design SKILL must pin render-exit carve-out in preamble and Step 5c item 5'
if grep -Fq 'Binding: markers `LARCH_FINAL_SUMMARY_BEGIN` / `LARCH_FINAL_SUMMARY_END`' "$design_skill"; then
    fail 'design SKILL must not retain marker-body Binding restatement'
fi
pointer_count=$(grep -cF 'skills/shared/final-summary-emit.md' "$design_skill") || pointer_count=0
test "$pointer_count" -ge 5 || fail 'design SKILL must point final-summary emit sites to shared final-summary emit contract'
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
  'extracted marker body defined in Step 17'
)
for retired in "${retired_prose[@]}"; do
  if git -C "$REPO" grep -Fq -- "$retired" skills/design/SKILL.md skills/implement/SKILL.md; then
    fail "retired cost-line-only prose remains: $retired"
  fi
done
pass 'retired cost-line-only prose absent from SKILL.md'

printf 'PASS: test-render-cost-line-callsites.sh\n'
