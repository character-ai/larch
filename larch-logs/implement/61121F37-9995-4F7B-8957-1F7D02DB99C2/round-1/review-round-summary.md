# Review Round 1

- Mode: `diff`
- 26 accepted, 5 rejected (3 exonerated)

## Accepted Findings

### FINDING_1: code-quality: scripts/test-render-cost-line-callsites.sh
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Plan-required SKILL.md grep invariants were not added The file is unchanged; regressions of Step 18 conditional print, SUMMARY_MODE_STRING=N/A, NEVER #20, or orchestrator cost-line emit prose will not fail make lint Extend test-render-cost-line-callsites.sh with the five grep assertions from the plan
- **Suggested revision**: Address the concern above.


### FINDING_10: risk-integration: skills/design/scripts/test-render-final-summary.sh:33-187
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Parameterized ten-outcome design matrix is incomplete: cancelled-already-planned, cancelled-sprawl, cancelled-plan-size-hard, and failed-plan-write are missing; some cancellation tests omit cost-line checks. Early-cancel or failed-plan-write summaries could lose cost lines without harness failure. Extend test-render-final-summary.sh to cover all ten outcomes and grep - **Cost**: on every --post-publish-only run.
- **Suggested revision**: Address the concern above.


### FINDING_11: risk-integration: skills/implement/scripts/test-write-final-report.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] No test supplies corrupt or jq-unparseable token-report.json to pin _no_token_data leading to --cost-unavailable (plan OOS #2915 side effect). Corrupt token JSON could regress to misleading Claude $0.00, Codex $0.00, Cursor $0.00 in chat summaries. Add a malformed token-report.json fixture and assert - **Cost**: N/A and absence of zero-dollar breakdown text.
- **Suggested revision**: Address the concern above.


### FINDING_12: risk-integration: scripts/test-render-run-summary.sh:791-840
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Plan edge case requires --cost-unavailable to win when combined with explicit nonzero token flags; only separate N/A and zero-default cases exist. Future renderer changes could honor token flags over --cost-unavailable and show wrong dollars while tests pass. Add one render-run-summary.sh call with --cost-unavailable plus nonzero token args; assert - **Cost**: N/A.
- **Suggested revision**: Address the concern above.


### FINDING_13: risk-integration: skills/implement/scripts/test-write-final-report.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Plan FINDING_31 PR bullet conditional (omit when pr_disp=N/A) is not asserted in the implement harness. PR bullet could reappear on N/A paths or disappear when a PR exists without test failure. Add paired fixtures asserting - **PR**: presence for pr-created and absence for bailed/N/A paths on --print-stdout output.
- **Suggested revision**: Address the concern above.


### FINDING_14: risk-integration: scripts/test-render-cost-line-callsites.md
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Plan listed updating/creating test-render-cost-line-callsites.md sibling; file is absent. Documentation drift for the callsite lint harness per repo script-md sibling convention. Add a short stub .md describing the grep contract exercised by test-render-cost-line-callsites.sh.
- **Suggested revision**: Address the concern above.


### FINDING_15: risk-integration: skills/design/scripts/test-render-final-summary.sh:114-141
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Token-data-missing test checks output N/A only, not that render-run-summary.sh received --cost-unavailable. Reverting to empty COST_ARGS=() could still emit N/A by accident in some paths while breaking the intended argv contract. Use a recording render-run-summary.sh stub and assert --cost-unavailable in argv for the token-failure invocation.
- **Suggested revision**: Address the concern above.


### FINDING_18: risk-integration: scripts/test-render-cost-line-callsites.sh:1-34
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Planned SKILL.md grep pins for Step 17/18 --print-stdout orchestrator cost emit NEVER #20 and SUMMARY_MODE_STRING were not added to the callsite harness. A future edit can remove collapse-resistant cost prose or conditional Step 18 print while CI stays green. Extend test-render-cost-line-callsites.sh with the planned grep -Fq assertions from the implementation plan.
- **Suggested revision**: Address the concern above.


### FINDING_19: correctness: skills/design/scripts/render-final-summary.sh:366-368
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Pre-phase render_or_fallback can write N/A fallback into final-summary.md that design-log-publish commits before post-phase re-render fixes chat only. Happy path pre render fails post succeeds: chat shows real per-agent cost but committed larch-logs/design/*/final-summary.md keeps Cost N/A from pre. Skip self-composed fallback on PHASE=pre fail pre on renderer error or re-publish after post when pre used fallback.
- **Suggested revision**: Address the concern above.


### FINDING_2: code-quality: skills/implement/scripts/test-write-final-report.sh:163-293
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] skills/design/scripts/test-render-final-summary.sh:69-173 No parameterized terminal-outcome matrices Acceptance criteria 2/3 are only partially covered by spot tests; merged/stalled/design-only/forked-dry-run/pr-created and several design cancelled-* paths lack harness coverage Add table-driven loops over all planned outcomes with schema assertions per outcome
- **Suggested revision**: Address the concern above.


### FINDING_20: correctness: skills/design/scripts/render-final-summary.sh:130-161
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] _cost_unavailable is set only when bucket sum is zero and stderr is non-empty; clean stderr with valid empty JSON still passes zero token flags. token-report.sh exits 0 writes parseable all-zero JSON with empty stderr: summary shows $0.00 instead of N/A on design terminal summary. Treat jq_ok with sum_b=0 as unavailable unless non-zero totals exist or widen FINDING_12 trigger beyond stderr_nonempty.
- **Suggested revision**: Address the concern above.


### FINDING_21: correctness: skills/implement/SKILL.md:1751-1758
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Step 17 cost-line orchestrator emit is not gated on write-final-report success unlike .step17-printed. write-final-report.sh exits non-zero at Step 17: model may still emit a stale Cost line from summary-final.md while sentinel is absent and Step 18 may later touch sentinel after failed print. Gate verbatim cost-line emit on the same condition as touch .step17-printed and require a present Cost line in summary-final.md.
- **Suggested revision**: Address the concern above.


### FINDING_22: risk-integration: skills/implement/scripts/test-write-final-report.sh:106-333
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Parameterized nine-outcome matrix from the plan is incomplete in tests. Regressions in forked-dry-run pr-created pr-created-draft or force-merged-externally cost or PR bullet shaping will not fail CI. Add harness cases for the four missing terminal outcomes with cost-line and conditional Outcome or PR assertions.
- **Suggested revision**: Address the concern above.


### FINDING_23: risk-integration: skills/design/scripts/test-render-final-summary.sh:158-187
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Full ten-outcome design matrix from the plan is not exercised. Self-composed fallback schema drift for e.g. failed-plan-write or cancelled-sprawl will not be caught by tests. Loop all design terminal outcomes through post-publish render with shared bullet-order assertions.
- **Suggested revision**: Address the concern above.


### FINDING_24: correctness: skills/implement/SKILL.md:1812-1814
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Step 18 touches .step17-printed after attempting --print-stdout even when write-final-report fails due to || true. Step 18 render fails silently: sentinel is set chat has no structured block and bail path cannot retry print in the same session. Touch sentinel only when write-final-report succeeds or stdout contains the summary title line.
- **Suggested revision**: Address the concern above.


### FINDING_25: correctness: scripts/test-render-run-summary.sh:791-840
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] No test that --cost-unavailable overrides explicit non-zero token flags. Future render-run-summary.sh regression could honor token flags when cost-unavailable is set yielding wrong dollars instead of N/A. Add one test passing --cost-unavailable plus non-zero token args asserting Cost N/A.
- **Suggested revision**: Address the concern above.


### FINDING_28: correctness: scripts/test-render-cost-line-callsites.sh
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Planned SKILL.md callsite and NEVER/cost-line grep pins were not added Acceptance #5 and Testing strategy require CI enforcement of Step 17/18 conditional print orchestrator cost emit SUMMARY_MODE_STRING N/A and NEVER prose; regressions ship silently Add the seven grep assertions from the plan to test-render-cost-line-callsites.sh and document in the sibling .md
- **Suggested revision**: Address the concern above.


### FINDING_29: **correctness** `skills/implement/scripts/write-final-report.sh:404-407` and `skills/design/scripts/render-final-summary.sh:342-345` — `compose_self_fallback()` formats `- **OOS filed**:` with `[ -n "${OOS_URLS:-}" ]` only, while `scripts/render-run-summary.sh:206-211` also requires `[ "$OOS_URLS" != "N/A" ]` before emitting the `count — urls` form. If `OOS_URLS` is ever the literal `N/A` with a non-zero count, the self-composed fallback would print `- **OOS filed**: <n> — N/A` on every renderer-fail path, which does not match the canonical renderer body. **Suggested fix:** Mirror the renderer guard in both fallbacks: `if [ "${OOS_COUNT:-0}" != "0" ] && [ -n "${OOS_URLS:-}" ] && [ "${OOS_URLS:-}" != "N/A" ]; then … else … fi`.
- **Reviewer**: dyn-fallback-schema-parity-output.txt
- **Concern**: - **correctness** `skills/implement/scripts/write-final-report.sh:404-407` and `skills/design/scripts/render-final-summary.sh:342-345` — `compose_self_fallback()` formats `- **OOS filed**:` with `[ -n "${OOS_URLS:-}" ]` only, while `scripts/render-run-summary.sh:206-211` also requires `[ "$OOS_URLS" != "N/A" ]` before emitting the `count — urls` form. If `OOS_URLS` is ever the literal `N/A` with a non-zero count, the self-composed fallback would print `- **OOS filed**: <n> — N/A` on every renderer-fail path, which does not match the canonical renderer body. **Suggested fix:** Mirror the renderer guard in both fallbacks: `if [ "${OOS_COUNT:-0}" != "0" ] && [ -n "${OOS_URLS:-}" ] && [ "${OOS_URLS:-}" != "N/A" ]; then … else … fi`.
- **Suggested revision**: Address the concern above.


### FINDING_30: **correctness** `skills/implement/scripts/test-write-final-report.sh:272-276` — Stage-2 renderer-fail coverage only checks `- **Cost**: N/A`, `- **Code review**:`, and the sentinel. It does not assert the conditional schema that `compose_self_fallback()` is meant to mirror: `- **Outcome**:` for the `bailed` fixture (`impl_bl`, lines 164–176), omission of `- **PR**:` when `PR_NUMBER` is empty, or post-sentinel `notes_tmp` content for outcomes like `forked-dry-run`. A regression in Outcome/PR ordering or notes placement would not fail CI. **Suggested fix:** Extend the Stage-2 case with `assert_contains` / `assert_not_contains` for `- **Outcome**: bailed`, absence of `- **PR**:`, and (for a `forked-dry-run` fixture) content after `<!-- larch:run-summary v=1 -->`.
- **Reviewer**: dyn-fallback-schema-parity-output.txt
- **Concern**: - **correctness** `skills/implement/scripts/test-write-final-report.sh:272-276` — Stage-2 renderer-fail coverage only checks `- **Cost**: N/A`, `- **Code review**:`, and the sentinel. It does not assert the conditional schema that `compose_self_fallback()` is meant to mirror: `- **Outcome**:` for the `bailed` fixture (`impl_bl`, lines 164–176), omission of `- **PR**:` when `PR_NUMBER` is empty, or post-sentinel `notes_tmp` content for outcomes like `forked-dry-run`. A regression in Outcome/PR ordering or notes placement would not fail CI. **Suggested fix:** Extend the Stage-2 case with `assert_contains` / `assert_not_contains` for `- **Outcome**: bailed`, absence of `- **PR**:`, and (for a `forked-dry-run` fixture) content after `<!-- larch:run-summary v=1 -->`.
- **Suggested revision**: Address the concern above.


### FINDING_31: **correctness** `skills/design/scripts/test-render-final-summary.sh:99-110` — The renderer-fail fallback test only pins `- **Cost**: N/A` and stdout/file byte identity. It never asserts design-schema suppression (no `- **PR**:` or `- **Code review**:`) or conditional `- **Outcome**:` bullets, so `compose_self_fallback()` in `render-final-summary.sh:323-351` could diverge from `render-run-summary.sh`’s `--skill design` rules without failing the harness. **Suggested fix:** After the fallback run, add `grep -Fq` negated checks for `- **PR**:` and `- **Code review**:`, plus positive checks for Outcome on a cancelled outcome (e.g. re-run with `cancelled-clarify` and a failing renderer stub).
- **Reviewer**: dyn-fallback-schema-parity-output.txt
- **Concern**: - **correctness** `skills/design/scripts/test-render-final-summary.sh:99-110` — The renderer-fail fallback test only pins `- **Cost**: N/A` and stdout/file byte identity. It never asserts design-schema suppression (no `- **PR**:` or `- **Code review**:`) or conditional `- **Outcome**:` bullets, so `compose_self_fallback()` in `render-final-summary.sh:323-351` could diverge from `render-run-summary.sh`’s `--skill design` rules without failing the harness. **Suggested fix:** After the fallback run, add `grep -Fq` negated checks for `- **PR**:` and `- **Code review**:`, plus positive checks for Outcome on a cancelled outcome (e.g. re-run with `cancelled-clarify` and a failing renderer stub).
- **Suggested revision**: Address the concern above.


### FINDING_35: **risk-integration** `skills/design/scripts/render-final-summary.sh:373-379` — The new post-phase chat-print loop copies `write-final-report.sh`’s `LARCH_QUIET_PID` / `>&3` routing, but unlike `skills/implement/scripts/write-final-report.sh:10-13` this script never sources `scripts/lib-quiet.sh` or calls `larch_quiet_init`. `render-final-summary.sh` is always a child process; without init, `LARCH_QUIET_PID` is never set to the child’s `$$`, so the `>&3` branch is dead and every summary line goes to stdout. That matches today’s SKILL.md direct Bash invocations (and matches the pre-change `--print-stdout` path through `render-run-summary.sh`, which also lacked quiet init), but it diverges from the implement terminal path where `write-final-report.sh` binds quiet mode and routes contract output to FD 3. `skills/design/scripts/render-final-summary.md:48-52` documents an “FD-3-aware chat loop” that is not actually reachable. If `LARCH_QUIET_PID` were ever exported as `$$` without a prior `exec 3>&1`, the `>&3` writes would hit a bad descriptor under `set -euo pipefail` and could abort before the tracking-issue upsert at `render-final-summary.sh:381-396`. **Suggested fix:** At the top of `render-final-summary.sh` (after `DESIGN_TMPDIR` validation), source `scripts/lib-quiet.sh` and call `larch_quiet_init`, mirroring `write-final-report.sh`, so the FD 3 branch is live and implement/design share one quiet contract; alternatively drop the `>&3` branch and document stdout-only chat printing explicitly if design is intentionally non-quiet.
- **Reviewer**: dyn-fd-quiet-print-routing-output.txt
- **Concern**: - **risk-integration** `skills/design/scripts/render-final-summary.sh:373-379` — The new post-phase chat-print loop copies `write-final-report.sh`’s `LARCH_QUIET_PID` / `>&3` routing, but unlike `skills/implement/scripts/write-final-report.sh:10-13` this script never sources `scripts/lib-quiet.sh` or calls `larch_quiet_init`. `render-final-summary.sh` is always a child process; without init, `LARCH_QUIET_PID` is never set to the child’s `$$`, so the `>&3` branch is dead and every summary line goes to stdout. That matches today’s SKILL.md direct Bash invocations (and matches the pre-change `--print-stdout` path through `render-run-summary.sh`, which also lacked quiet init), but it diverges from the implement terminal path where `write-final-report.sh` binds quiet mode and routes contract output to FD 3. `skills/design/scripts/render-final-summary.md:48-52` documents an “FD-3-aware chat loop” that is not actually reachable. If `LARCH_QUIET_PID` were ever exported as `$$` without a prior `exec 3>&1`, the `>&3` writes would hit a bad descriptor under `set -euo pipefail` and could abort before the tracking-issue upsert at `render-final-summary.sh:381-396`. **Suggested fix:** At the top of `render-final-summary.sh` (after `DESIGN_TMPDIR` validation), source `scripts/lib-quiet.sh` and call `larch_quiet_init`, mirroring `write-final-report.sh`, so the FD 3 branch is live and implement/design share one quiet contract; alternatively drop the `>&3` branch and document stdout-only chat printing explicitly if design is intentionally non-quiet.
- **Suggested revision**: Address the concern above.


### FINDING_39: **correctness** `skills/implement/scripts/write-final-report.sh:233-257` — `refresh_issue_counts` adds two incompatible tallies: `grep -c '"category":"Warnings"'` / `'"category":"Tool Failures"'` on `larch-logs/implement/<RUN_ID>/execution-issues.ndjson` counts **one NDJSON record per flushed `###` section** (see `scripts/lib-execution-issues.sh:95-156` and `skills/implement/scripts/test-flush-execution-issues.sh:176-177`, where two sections yield `RECORDS=2`), while the new awk rule counts **individual** `- **Step …` bullets in `$IMPLEMENT_TMPDIR/execution-issues.md`. After a successful Step 7a flush, `flush-execution-issues.sh` clears the markdown log (`skills/implement/scripts/flush-execution-issues.sh:181-183`) but leaves prior issues inside NDJSON bodies, so post–Step 17 fallback warnings only exist as new markdown bullets; summing `WARN_N=$((WARN_N + md_warn))` mixes “section records” with “bullet lines” and under-reports real warnings when a single NDJSON record embeds multiple `- **Step` entries. If flush fails and markdown is not cleared while NDJSON already contains the same section, the same bullets can be counted twice (NDJSON line + each markdown line). **Suggested fix:** Treat live markdown as authoritative when `$IMPLEMENT_TMPDIR/execution-issues.md` is non-empty (awk only, same `/^- \*\*Step /` rule). When markdown is empty after flush, count bullets inside NDJSON `body` fields with the same awk pattern (or document and test section-level semantics explicitly)—do not add NDJSON line count and markdown bullet count together.
- **Reviewer**: dyn-awk-count-pattern-output.txt
- **Concern**: - **correctness** `skills/implement/scripts/write-final-report.sh:233-257` — `refresh_issue_counts` adds two incompatible tallies: `grep -c '"category":"Warnings"'` / `'"category":"Tool Failures"'` on `larch-logs/implement/<RUN_ID>/execution-issues.ndjson` counts **one NDJSON record per flushed `###` section** (see `scripts/lib-execution-issues.sh:95-156` and `skills/implement/scripts/test-flush-execution-issues.sh:176-177`, where two sections yield `RECORDS=2`), while the new awk rule counts **individual** `- **Step …` bullets in `$IMPLEMENT_TMPDIR/execution-issues.md`. After a successful Step 7a flush, `flush-execution-issues.sh` clears the markdown log (`skills/implement/scripts/flush-execution-issues.sh:181-183`) but leaves prior issues inside NDJSON bodies, so post–Step 17 fallback warnings only exist as new markdown bullets; summing `WARN_N=$((WARN_N + md_warn))` mixes “section records” with “bullet lines” and under-reports real warnings when a single NDJSON record embeds multiple `- **Step` entries. If flush fails and markdown is not cleared while NDJSON already contains the same section, the same bullets can be counted twice (NDJSON line + each markdown line). **Suggested fix:** Treat live markdown as authoritative when `$IMPLEMENT_TMPDIR/execution-issues.md` is non-empty (awk only, same `/^- \*\*Step /` rule). When markdown is empty after flush, count bullets inside NDJSON `body` fields with the same awk pattern (or document and test section-level semantics explicitly)—do not add NDJSON line count and markdown bullet count together.
- **Suggested revision**: Address the concern above.


### FINDING_6: code-quality: scripts/render-run-summary.sh:28-30
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] usage() omits --cost-unavailable Operators relying on -h/--help may not discover the flag Add --cost-unavailable to usage() or a see render-run-summary.md pointer
- **Suggested revision**: Address the concern above.


### FINDING_7: correctness: skills/implement/scripts/write-final-report.sh:233-257
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] refresh_issue_counts sums ndjson category lines plus md warning bullets 2 flushed warnings in ndjson plus 3 md bullets after fallback append yields WARN_N=5 in summary though only 3 distinct warnings Use one source of truth: prefer md when present else ndjson only, matching plan re-grep semantics
- **Suggested revision**: Address the concern above.


### FINDING_8: risk-integration: scripts/test-render-cost-line-callsites.sh:1-34
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Plan acceptance #5 required grep pins for Step 17/18 print-stdout, design post-publish-only, SUMMARY_MODE_STRING N/A default, NEVER recap rules, and orchestrator cost-line emit prose; the file was not updated in the diff. SKILL.md contract regressions (e.g. removing orchestrator cost-line emit or Step 18 conditional print) will not fail CI despite being plan acceptance gates. Add the seven grep -Fq assertions from the plan to test-render-cost-line-callsites.sh and document them in a new sibling .md stub.
- **Suggested revision**: Address the concern above.


### FINDING_9: risk-integration: skills/implement/scripts/test-write-final-report.sh:52-333
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Parameterized nine-outcome chat-print matrix from the plan is incomplete: forked-dry-run, pr-created, pr-created-draft, and force-merged-externally are untested; several existing outcomes lack --print-stdout cost-line assertions. A regression in outcome mapping or cost rendering for pr-created/forked/force-merged paths could ship while CI stays green. Add a shared loop over all nine outcomes with --print-stdout asserting - **Cost**:, sentinel, conditional Outcome, and PR bullet rules.
- **Suggested revision**: Address the concern above.


