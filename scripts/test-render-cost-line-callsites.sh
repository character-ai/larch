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
grep -Fq 'skills/shared/final-summary-emit.md' "$REPO/skills/implement/SKILL.md" || fail 'implement SKILL must point to shared final-summary emit contract'
# shellcheck disable=SC2016
grep -Fq 'markers `---LARCH-SUMMARY-FINAL-BEGIN---` / `---LARCH-SUMMARY-FINAL-END---`' "$REPO/skills/implement/SKILL.md" || fail 'implement SKILL must bind implement marker pair'
# shellcheck disable=SC2016
grep -Fq 'captured foreground `python/cli.py implement step-16-17` Bash wrapper stdout' "$REPO/skills/implement/SKILL.md" || fail 'implement SKILL must bind Step 17 captured foreground stdout source'
# shellcheck disable=SC2016
grep -Fq 'captured foreground `step-18.sh --phase finalize` Bash wrapper stdout' "$REPO/skills/implement/SKILL.md" || fail 'implement SKILL must bind Step 18b captured foreground stdout source'
grep -Fq 'not `<task-notification>` output' "$REPO/skills/implement/SKILL.md" || fail 'implement SKILL must forbid task-notification as implement summary source'
grep -Fq 'Read fallback `forbidden`' "$REPO/skills/implement/SKILL.md" || fail 'implement SKILL must forbid Read fallback for Step 17/18b'
grep -Fq 'sidecar follow-on `forbidden`' "$REPO/skills/implement/SKILL.md" || fail 'implement SKILL must forbid sidecar follow-on for Step 17/18b'
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
grep -Fq 'When the shared profile emits a non-empty marker body as plain chat markdown, write `$IMPLEMENT_TMPDIR/.step17-emitted` only after that plain-chat emission.' "$REPO/skills/implement/SKILL.md" || fail 'implement SKILL must pin Step 17 sentinel after shared emit'
# shellcheck disable=SC2016
grep -Fq 'The only orchestrator-text addition permitted after the Bash summary is the verbatim full-body emission from the shared marker-first profile using the Step 17 source or the Step 18b source.' "$REPO/skills/implement/SKILL.md" || fail 'implement SKILL must pin NEVER #17 shared-profile exception prose'
grep -Fq 'NEVER write a free-form natural-language recap summary at end of turn after Step 17' "$REPO/skills/implement/SKILL.md" || fail 'implement SKILL must pin NEVER #20 literal'
grep -Fq -- '--post-publish-only' "$design_skill" || fail 'design SKILL must call render-final-summary.sh with --post-publish-only'
# shellcheck disable=SC2016
grep -Fq 'emit its full body verbatim as plain chat markdown' "$shared_final_summary" || fail 'shared final-summary emit must pin full-body emit prose'
grep -Fq 'Caller profile parameters' "$shared_final_summary" || fail 'shared final-summary emit must define caller profile parameters'
grep -Fq 'caller begin/end marker pair' "$shared_final_summary" || fail 'shared final-summary emit must parameterize marker tokens'
grep -Fq 'caller-named task-output source already in the orchestrator context window' "$shared_final_summary" || fail 'shared final-summary emit must parameterize task-output source'
grep -Fq '`/implement` binds captured foreground Bash wrapper stdout, not `<task-notification>`.' "$shared_final_summary" || fail 'shared final-summary emit must distinguish implement source from task notifications'
# shellcheck disable=SC2016
grep -Fq 'Only when the caller Read fallback policy is `allowed`, Read the caller-named fallback path when non-empty.' "$shared_final_summary" || fail 'shared final-summary emit must gate Read fallback on caller policy'
grep -Fq 'When the caller Read fallback policy is `forbidden`, skip Read fallback entirely.' "$shared_final_summary" || fail 'shared final-summary emit must define forbidden Read fallback'
grep -Fq 'Only when the caller sidecar policy is `allowed`' "$shared_final_summary" || fail 'shared final-summary emit must gate sidecar follow-on on caller policy'
grep -Fq 'When the caller sidecar policy is `forbidden`, skip sidecar follow-on entirely.' "$shared_final_summary" || fail 'shared final-summary emit must define forbidden sidecar follow-on'
# shellcheck disable=SC2016
grep -Fq 'Do not re-read task-output files, stdout captures, result env files, or tmpdir logs to recover markers.' "$shared_final_summary" || fail 'shared final-summary emit must forbid task-output re-reads'
grep -Fq 'Do not scrape markers via Bash or Python.' "$shared_final_summary" || fail 'shared final-summary emit must forbid Bash/Python marker scraping'
grep -Fq '`/design` marker-first' "$shared_final_summary" || fail 'shared final-summary emit must include design callsite binding'
grep -Fq '`/implement` Step 17 marker-first' "$shared_final_summary" || fail 'shared final-summary emit must include implement Step 17 callsite binding'
grep -Fq '`/implement` Step 18b marker-first' "$shared_final_summary" || fail 'shared final-summary emit must include implement Step 18b callsite binding'
grep -Fq 'Skip marker extraction entirely; do not scan prior tool output for markers.' "$shared_final_summary" || fail 'shared final-summary emit must pin file-only no-marker behavior'

# shellcheck disable=SC2016
grep -Fq 'defined in `${CLAUDE_PLUGIN_ROOT}/skills/shared/final-summary-emit.md` marker-first profile' "$design_skill" || fail 'design SKILL anti-halt must point to shared marker-first profile'
grep -Fq 'applies when `_publish_rc` is 0, 1, or 3' "$design_skill" || fail 'design SKILL must pin post-driver full-body emit gate with rc 4 carve-out'
grep -Fq 'Binding: markers `LARCH_FINAL_SUMMARY_BEGIN` / `LARCH_FINAL_SUMMARY_END`; source completed `design-step5c.sh` `<task-notification>` stdout already in context' "$design_skill" || fail 'design SKILL must bind Step 5c marker source'
grep -Fq 'Binding: markers `LARCH_FINAL_SUMMARY_BEGIN` / `LARCH_FINAL_SUMMARY_END`; source completed `design-step-final-summary.sh` `<task-notification>` stdout already in context' "$design_skill" || fail 'design SKILL must bind cancellation marker source'
grep -Fq 'Read fallback and sidecar follow-on per the shared `/design` callsite row' "$design_skill" || fail 'design SKILL must bind design fallback and sidecar policies'
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
python3 - "$design_skill" <<'PY_DESIGN_BINDINGS'
from pathlib import Path
import sys
path = Path(sys.argv[1])
for lineno, line in enumerate(path.read_text().splitlines(), start=1):
    if 'marker-first profile' in line and 'shared marker-first profile' not in line:
        if 'LARCH_FINAL_SUMMARY_BEGIN` / `LARCH_FINAL_SUMMARY_END' not in line or '<task-notification>' not in line:
            raise SystemExit(f'design marker-first callsite missing adjacent binding on line {lineno}')
PY_DESIGN_BINDINGS
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
