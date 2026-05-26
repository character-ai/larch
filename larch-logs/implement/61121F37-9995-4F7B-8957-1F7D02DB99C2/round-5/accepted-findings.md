### FINDING_1: code-quality: scripts/test-render-cost-line-callsites.sh:40
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Callsite lint greps a Step 18 Bash pattern that no longer exists in implement SKILL.md. Running make lint or scripts/test-render-cost-line-callsites.sh fails on this branch (verified). Update the grep pin to match the current _wfr_emit_cost/_wfr_new_cost touch guard or replace substring lint with a harness that executes the Step 18 fence.
- **Suggested revision**: Address the concern above.


### FINDING_13: risk-integration: scripts/test-render-cost-line-callsites.sh:40
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Grep pin expects Step 18 touch gated on `_wfr_printed=true` plus cost-line grep, but SKILL.md now uses `_wfr_emit_cost` and cost-change detection. Running `make lint` / `test-render-cost-line-callsites` fails even when Step 18 behavior is correct, blocking merge. Update the pin to match current Step 18 bash (grep `_wfr_emit_cost` / refreshed-cost branch or a stable substring from SKILL.md:1828).
- **Suggested revision**: Address the concern above.


### FINDING_14: risk-integration: scripts/test-render-cost-line-callsites.sh:43
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Grep pin for Step 18 orchestrator-text emit prose no longer matches reordered SKILL.md text after round 4. Same harness fails CI on a prose-only SKILL refinement that did not regress runtime behavior. Replace stale literal with grep for substrings present in the current Step 18 emit paragraph at skills/implement/SKILL.md:1828.
- **Suggested revision**: Address the concern above.


### FINDING_15: risk-integration: skills/implement/scripts/test-write-final-report.sh:491-514
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Nine-outcome matrix validates `--print-stdout` only; never asserts `$fixture/summary-final.md`. Chat print and persisted summary could diverge without failing CI, violating plan dual-assertion and design harness parity. Assert the same markers on summary-final.md each iteration; compare summary body in stdout (pre-STATUS lines) to the file.
- **Suggested revision**: Address the concern above.


### FINDING_16: risk-integration: skills/design/scripts/test-render-final-summary.sh:98-106
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Per-agent breakdown happy path checks markers only in final-summary.md, not post-phase stdout. Post-phase chat-print could lose per-agent breakdown while the file still passes, missing acceptance #4 chat-output intent. Grep std_codex for the same five markers or cmp stdout to final-summary.md in that case.
- **Suggested revision**: Address the concern above.


### FINDING_24: security: skills/implement/scripts/write-final-report.sh:443-447
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] wfr-fallback-stage1.log retains unredacted renderer stderr on disk API/auth tokens in token-cost stderr may persist locally until tmpdir cleanup Redact or delete sidecar after append-tool-failure --redact
- **Suggested revision**: Address the concern above.


### FINDING_27: correctness: scripts/test-render-cost-line-callsites.sh:40
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Callsite lint greps for a Step 18 Bash fragment that is not in implement SKILL.md. make lint fails every build though Step 18 conditional print is implemented elsewhere. Update grep to match _wfr_emit_cost / touch .step17-printed block in skills/implement/SKILL.md.
- **Suggested revision**: Address the concern above.


### FINDING_28: correctness: scripts/test-render-cost-line-callsites.sh:46
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Step 18 grep pins sentinel-touch logic (_wfr_printed && cost-line grep) that is not in implement SKILL.md. test-render-cost-line-callsites.sh exits 1 today (FAIL: Step 18 must gate .step17-printed…), so make lint / acceptance gate 7 fails even though runtime scripts are updated. Update greps to match the shipped _wfr_emit_cost / _wfr_new_cost Step 18 block, or restore SKILL prose the test expects.
- **Suggested revision**: Address the concern above.


### FINDING_29: correctness: scripts/test-render-cost-line-callsites.sh:49
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Step 18 orchestrator cost-line emit grep uses stale prose not present in implement SKILL.md. After fixing line 46, the harness would fail on the Step 18 emit substring; gate 5 prose pins are not fully enforced. Change the grep to the current paragraph at skills/implement/SKILL.md:1828 (sentinel absent OR cost changed).
- **Suggested revision**: Address the concern above.


### FINDING_31: correctness: Plan acceptance gate 8
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] OOS #2915 acknowledgment comment is required by the plan but not present in the branch. Tracking issue may stay open after merge despite corrupt-JSON fix landing in code. Post the brief closure comment on #2915 when shipping.
- **Suggested revision**: Address the concern above.


### FINDING_32: **correctness** `skills/implement/scripts/write-final-report.sh:249-263` — When `$IMPLEMENT_TMPDIR/execution-issues.md` is missing or empty, `refresh_issue_counts` falls through to `jq -r '.body // empty' "$run_dir/execution-issues.ndjson" | awk …`. NDJSON `body` fragments are bare bullets (no `### Tool Failures` / `### Warnings` headers), so the section-aware awk never sets `sec` and every `- **Step …` line is ignored; `EXEC_N`/`WARN_N` stay 0 even when flushed NDJSON has warning records. Round 4 removed the upfront `grep -c '"category":"Warnings"'` block, so this path is easier to hit on early-bail / empty-md runs than on main. **Suggested fix:** For the NDJSON branch, keep the old category `grep -c` counts when the piped body lacks section headers (detect with `grep -q '^### Warnings$'` on the combined stream), or rebuild per-category bodies with `jq` before awk (e.g. filter by `.category` and wrap with the right `###` header).
- **Reviewer**: dyn-bash-mechanics-output.txt
- **Concern**: - **correctness** `skills/implement/scripts/write-final-report.sh:249-263` — When `$IMPLEMENT_TMPDIR/execution-issues.md` is missing or empty, `refresh_issue_counts` falls through to `jq -r '.body // empty' "$run_dir/execution-issues.ndjson" | awk …`. NDJSON `body` fragments are bare bullets (no `### Tool Failures` / `### Warnings` headers), so the section-aware awk never sets `sec` and every `- **Step …` line is ignored; `EXEC_N`/`WARN_N` stay 0 even when flushed NDJSON has warning records. Round 4 removed the upfront `grep -c '"category":"Warnings"'` block, so this path is easier to hit on early-bail / empty-md runs than on main. **Suggested fix:** For the NDJSON branch, keep the old category `grep -c` counts when the piped body lacks section headers (detect with `grep -q '^### Warnings$'` on the combined stream), or rebuild per-category bodies with `jq` before awk (e.g. filter by `.category` and wrap with the right `###` header).
- **Suggested revision**: Address the concern above.


### FINDING_33: **correctness** `skills/implement/scripts/write-final-report.sh:236-244` — The md-path awk only increments `ex`/`wa` on `/^- \*\*Step /`. Entries under `### External Reviewer Issues` such as `- **findings aggregator**:` (see `larch-logs/design/072C28F7-468B-43C4-9F71-28C635D34463/execution-issues.md:1-3`) never match, so `EXEC_N` in the final summary under-reports external-reviewer failures whenever a non-empty session `execution-issues.md` exists. Main counted NDJSON records via `grep -c '"category":"External Reviewer Issues"'` (and siblings), so this is a behavioral regression for typical runs with a populated md log. **Suggested fix:** Under `sec == 1`, also count bullets matching `/^- \*\*(Step |findings aggregator)/` (or any non-empty `- **…` line in Tool Failures / External Reviewer sections), and add a harness case with an aggregator-only external-reviewer bullet asserting `EXEC_N >= 1`.
- **Reviewer**: dyn-bash-mechanics-output.txt
- **Concern**: - **correctness** `skills/implement/scripts/write-final-report.sh:236-244` — The md-path awk only increments `ex`/`wa` on `/^- \*\*Step /`. Entries under `### External Reviewer Issues` such as `- **findings aggregator**:` (see `larch-logs/design/072C28F7-468B-43C4-9F71-28C635D34463/execution-issues.md:1-3`) never match, so `EXEC_N` in the final summary under-reports external-reviewer failures whenever a non-empty session `execution-issues.md` exists. Main counted NDJSON records via `grep -c '"category":"External Reviewer Issues"'` (and siblings), so this is a behavioral regression for typical runs with a populated md log. **Suggested fix:** Under `sec == 1`, also count bullets matching `/^- \*\*(Step |findings aggregator)/` (or any non-empty `- **…` line in Tool Failures / External Reviewer sections), and add a harness case with an aggregator-only external-reviewer bullet asserting `EXEC_N >= 1`.
- **Suggested revision**: Address the concern above.


### FINDING_38: **correctness** `skills/design/scripts/render-final-summary.sh:384-409` — `render_or_fallback` only restores `preserved_cost_line` when `invoke_render` fails or writes an empty file; if the post-publish call succeeds while `_cost_unavailable=true` (common when the second `token-report.sh` pass yields zero buckets or missing JSON), the renderer overwrites `final-summary.md` with `- **Cost**: N/A` and the pre-publish per-agent line is dropped even though it was captured. That breaks the stated “preserve prior usable cost” behavior on the happy-path two-phase `/design` flow (pre had a breakdown, post silently regresses to N/A). **Suggested fix:** After a successful `invoke_render`, if `PHASE=post`, `preserved_cost_line` is non-empty, and the new file’s cost line is N/A (or missing), run the same first-match `awk` substitution used on the failure branch; alternatively treat “usable cost in pre file + N/A in post success body” as a trigger for that substitution.
- **Reviewer**: dyn-fallback-schema-fidelity-output.txt
- **Concern**: - **correctness** `skills/design/scripts/render-final-summary.sh:384-409` — `render_or_fallback` only restores `preserved_cost_line` when `invoke_render` fails or writes an empty file; if the post-publish call succeeds while `_cost_unavailable=true` (common when the second `token-report.sh` pass yields zero buckets or missing JSON), the renderer overwrites `final-summary.md` with `- **Cost**: N/A` and the pre-publish per-agent line is dropped even though it was captured. That breaks the stated “preserve prior usable cost” behavior on the happy-path two-phase `/design` flow (pre had a breakdown, post silently regresses to N/A). **Suggested fix:** After a successful `invoke_render`, if `PHASE=post`, `preserved_cost_line` is non-empty, and the new file’s cost line is N/A (or missing), run the same first-match `awk` substitution used on the failure branch; alternatively treat “usable cost in pre file + N/A in post success body” as a trigger for that substitution.
- **Suggested revision**: Address the concern above.


### FINDING_43: **correctness** `scripts/test-render-cost-line-callsites.sh:40-43` — The callsite linter still greps for obsolete Step 18 shapes (`if [ "$_wfr_printed" = true ] && grep -Fq -- '- **Cost**:' ...` for sentinel gating, and the old single-condition Step 18 emit sentence) that were replaced in `skills/implement/SKILL.md:1810-1828` by `_wfr_emit_cost`, `_wfr_prev_cost`/`_wfr_new_cost` comparison, and the dual-condition emit prose. Running `bash scripts/test-render-cost-line-callsites.sh` exits 1 on line 40 today, so CI cannot enforce the sentinel/orchestrator contract the branch relies on. **Suggested fix:** Update the greps to pin the current Bash block (`_wfr_emit_cost`, `_wfr_new_cost != "$_wfr_prev_cost"`, and the line-1828 emit prose) so the linter matches the implemented semantics and passes.
- **Reviewer**: dyn-sentinel-orchestration-output.txt
- **Concern**: - **correctness** `scripts/test-render-cost-line-callsites.sh:40-43` — The callsite linter still greps for obsolete Step 18 shapes (`if [ "$_wfr_printed" = true ] && grep -Fq -- '- **Cost**:' ...` for sentinel gating, and the old single-condition Step 18 emit sentence) that were replaced in `skills/implement/SKILL.md:1810-1828` by `_wfr_emit_cost`, `_wfr_prev_cost`/`_wfr_new_cost` comparison, and the dual-condition emit prose. Running `bash scripts/test-render-cost-line-callsites.sh` exits 1 on line 40 today, so CI cannot enforce the sentinel/orchestrator contract the branch relies on. **Suggested fix:** Update the greps to pin the current Bash block (`_wfr_emit_cost`, `_wfr_new_cost != "$_wfr_prev_cost"`, and the line-1828 emit prose) so the linter matches the implemented semantics and passes.
- **Suggested revision**: Address the concern above.


### FINDING_7: correctness: scripts/test-render-cost-line-callsites.sh:40-43
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Stale grep pins for Step 18 sentinel and cost-emit prose no longer match skills/implement/SKILL.md after round-4 edits. bash scripts/test-render-cost-line-callsites.sh exits 1 at the Step 18 sentinel grep; make lint fails on this target. Update greps to match _wfr_emit_cost / _wfr_new_cost and current Step 18 orchestrator prose at skills/implement/SKILL.md:1817-1828.
- **Suggested revision**: Address the concern above.


### FINDING_8: correctness: skills/design/scripts/render-final-summary.sh:384-409
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] preserved_cost_line is restored only on render failure; successful post render with --cost-unavailable overwrites a pre-publish usable cost. Pre-publish writes real breakdown; post-publish token-report fails or is all-zero; post invoke_render succeeds with N/A; user loses per-agent costs in final-summary.md and chat. After successful post render, if preserved_cost_line is set and new cost is N/A, splice preserved line; or skip overwrite when pre file has usable cost.
- **Suggested revision**: Address the concern above.


