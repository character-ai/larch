### FINDING_1: code-quality: skills/implement/scripts/write-final-report.sh:162-181
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Implement path lacks design's all-zero token guard; parseable empty JSON can still render $0.00 breakdown. Token report exists with valid .claude.totals but zero totals/buckets; /implement chat shows misleading zero-dollar cost while /design shows N/A for the same data shape. Mirror render-final-summary.sh sum_b/total_t logic or shared helper; pass --cost-unavailable when both are zero.
- **Suggested revision**: Address the concern above.

### FINDING_2: correctness: skills/design/scripts/render-final-summary.sh:384-386
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Pre-publish uses render_or_fallback false so renderer failure exits 1 and leaves no final-summary.md while plan says fallback applies in both phases Step 5c item 7 Bash fails on transient render error; pre-commit log bundle may lack summary until post-publish item 9 Document as intentional in plan or enable Phase-1 self-compose with Cost N/A and exit 0
- **Suggested revision**: Address the concern above.

### FINDING_3: correctness: skills/design/SKILL.md:288
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Design mandates verbatim cost-line orchestrator emit after every post-publish call without success or grep gate unlike implement Step 17/18 Helper exits 2 but stale final-summary.md remains; agent may emit wrong cost line Require exit 0 and grep for - **Cost**: before orchestrator emit (match implement)
- **Suggested revision**: Address the concern above.

### FINDING_4: correctness: skills/design/scripts/render-final-summary.sh:136-150
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] jq_ok with all-zero buckets and totals sets _cost_unavailable without stderr Valid zero-token JSON shows Cost N/A instead of dollar-primary $0.00 breakdown Only set _cost_unavailable on stderr or trc failure when jq_ok; else pass zero token args
- **Suggested revision**: Address the concern above.

### FINDING_5: correctness: scripts/test-render-cost-line-callsites.sh:34-44
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Missing planned grep pin for design NEVER anti-recap prose Regression can remove design recap ban without CI failure Add grep -Fq for NEVER write a free-form natural-language recap in design SKILL.md
- **Suggested revision**: Address the concern above.

### FINDING_6: correctness: skills/implement/SKILL.md:73
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] NEVER 20 says sentinel always written after Step 17 success but code gates touch on cost line presence Model touches sentinel without cost line and blocks Step 18 conditional print Align NEVER 20 text with grep-gated touch in Step 17
- **Suggested revision**: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] correctness: skills/implement/scripts/write-final-report.sh:222-271
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] ndjson vs markdown execution-issue counting can diverge when both files exist Summary warnings count may not match committed ndjson until fallback refresh Unify counting source or sync md from ndjson (pre-existing)
- **Suggested revision**: Address the concern above.

### FINDING_8: risk-integration: skills/implement/scripts/test-write-final-report.sh:218-266
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Stage-1 fallback test is a false positive when token JSON is absent. Primary render already passes --cost-unavailable; stub succeeds on first call; degraded Stage-1 path never runs; CI cannot detect Stage-1 regression. Use valid token JSON plus a stub that fails first call and succeeds on second with --cost-unavailable; assert fallback log or invocation count.
- **Suggested revision**: Address the concern above.

### FINDING_9: risk-integration: scripts/test-render-cost-line-callsites.sh:34-44
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Missing plan-required greps for NEVER anti-recap and implement orchestrator cost-line emit prose. SKILL.md could drop NEVER #20 or Step 17 verbatim cost emit while callsite harness still passes. Add grep -Fq for NEVER substrings in both SKILL files and implement cost-line emit prose.
- **Suggested revision**: Address the concern above.

### FINDING_10: risk-integration: skills/design/scripts/test-render-final-summary.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] No test for --pre-publish-only chat suppression. PHASE=pre could regress to printing summary to chat, causing double-print on happy path 5c. Add pre-publish case: file non-empty, stdout lacks summary title/body.
- **Suggested revision**: Address the concern above.

### FINDING_11: risk-integration: skills/design/scripts/test-render-final-summary.sh:4
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Harness disables quiet mode for all design summary tests. Production FD 3 chat-print loop is untested; quiet routing bugs would not fail CI. Add optional quiet-mode subtest or document harness gap.
- **Suggested revision**: Address the concern above.

### FINDING_12: risk-integration: skills/design/scripts/test-render-final-summary.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No corrupt/malformed token JSON test on design path. Design FINDING_12 path could regress to misleading $0.00 without CI signal (OOS #2915). Mirror implement badjson fixture; assert Cost N/A and no zero-dollar breakdown.
- **Suggested revision**: Address the concern above.

### FINDING_13: risk-integration: skills/design/scripts/test-render-final-summary.sh:181-184
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Empty-mode test uses cancelled-tier-gate not cancelled-title-filter. Minor traceability gap vs plan FINDING_18 scenario naming. Use cancelled-title-filter outcome label in harness.
- **Suggested revision**: Address the concern above.

### FINDING_14: security: skills/implement/scripts/write-final-report.sh:274-287
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] append_render_warning embeds render stderr logs via append-tool-failure.sh without --redact Degraded render fallback captures stderr into wfr-fallback-stage1.log; if stderr contains a GitHub PAT or API key fragment, flush-execution-issues can commit it into larch-logs/implement/<RUN_ID>/execution-issues.ndjson Pass --redact on append-tool-failure.sh inside append_render_warning
- **Suggested revision**: Address the concern above.

### FINDING_15: architecture: skills/design/scripts/render-final-summary.sh:384-386
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Pre phase ignores render_or_fallback false failure and always exit 0 Phase-1 render fails file deleted design-log-publish commits without final-summary.md post fixes chat only Propagate pre failure or write pre fallback file without chat print
- **Suggested revision**: Address the concern above.

### FINDING_16: correctness: skills/design/scripts/render-final-summary.md:29-31
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Doc claims Phase-1 returns non-zero on render failure but code exits 0 Operators expect publish abort missing log artifact Align doc and code behavior
- **Suggested revision**: Address the concern above.

### FINDING_17: risk-integration: skills/implement/SKILL.md:1751-1760
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] ROOT CAUSE G cost-line emit is prose-only not mechanical Model skips emit user sees collapsed Bash only no visible cost Add shell helper for verbatim cost line emit
- **Suggested revision**: Address the concern above.

### FINDING_18: correctness: skills/implement/SKILL.md:1752-1753
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] grep -Fq for Cost substring sets step17-printed too broadly Note line contains substring blocks Step 18 conditional print Use anchored grep for canonical Cost bullet
- **Suggested revision**: Address the concern above.

### FINDING_19: correctness: skills/design/scripts/render-final-summary.sh:134-156
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] sum_b zero with nonzero totals uses aggregate tokens not cost-unavailable Partial token JSON shows misleading breakdown without buckets Treat missing buckets as cost unavailable
- **Suggested revision**: Address the concern above.

### FINDING_20: architecture: skills/design/scripts/render-final-summary.md:56-59
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Doc still describes **Step counting but awk uses - **Step Maintainer reverts awk from stale doc Wording in md sibling to match append-tool-failure format
- **Suggested revision**: Address the concern above.

### FINDING_21: correctness: scripts/test-render-cost-line-callsites.sh:34-44
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Callsite lint omits the plan-required grep for design anti-recap NEVER prose. A future edit could remove or weaken the design free-form recap ban while CI still passes; agents may resume emitting Design complete closers that hide canonical cost lines. Add grep -Fq for NEVER write a free-form natural-language recap summary at end of turn (or another stable substring) against skills/design/SKILL.md.
- **Suggested revision**: Address the concern above.

### FINDING_22: correctness: scripts/test-render-cost-line-callsites.sh:39-43
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Implement orchestrator cost-line emit prose is not grep-pinned per acceptance 5(g). ROOT CAUSE G implement instructions could be edited without failing test-render-cost-line-callsites.sh because only NEVER #20 exception text is pinned. Add grep -Fq for a stable substring from the Step 17 verbatim cost-line emit paragraph in skills/implement/SKILL.md.
- **Suggested revision**: Address the concern above.

### FINDING_23: correctness: skills/implement/scripts/test-write-final-report.sh:273-279
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Stage 2 renderer-fail test lacks the plan’s ordered-bullet assertion helper. Schema drift in compose_self_fallback could drop or reorder bullets while spot checks on Cost and Outcome still pass. Add a helper asserting full implement fallback bullet order or compare against a golden body.
- **Suggested revision**: Address the concern above.

### FINDING_24: [OUT_OF_SCOPE] correctness: skills/design/scripts/test-render-final-summary.sh:178-191
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Empty-mode test uses cancelled-tier-gate instead of plan-named cancelled-title-filter. None for the mechanism under test; only scenario naming differs from the plan. Optional: rename or duplicate the case with cancelled-title-filter for plan traceability.
- **Suggested revision**: Address the concern above.

### FINDING_25: **correctness** `skills/implement/SKILL.md:73` — NEVER #20 tells the orchestrator that Step 17 “writes `$IMPLEMENT_TMPDIR/.step17-printed`” after `write-final-report.sh` prints, but the Step 17 Bash fence only runs `touch` when `grep` finds `- **Cost**:` in `summary-final.md` (1751–1754). If the script exits 0 yet the file has no cost bullet (transient render bug, stale file, or partial write), the agent may assume Step 18 will not re-print while also skipping the collapse-resistant cost-line emit (1760 gates on the same condition). **Suggested fix:** Align NEVER #20 and the Step 17 orchestrator sub-step with the Bash guard—e.g. “touch `.step17-printed` only when `write-final-report.sh` succeeds and `summary-final.md` contains `- **Cost**:`”—or move the sentinel write into `write-final-report.sh` so script and SKILL prose share one contract.
- **Reviewer**: dyn-skill-prose-consistency-output.txt
- **Concern**: - **correctness** `skills/implement/SKILL.md:73` — NEVER #20 tells the orchestrator that Step 17 “writes `$IMPLEMENT_TMPDIR/.step17-printed`” after `write-final-report.sh` prints, but the Step 17 Bash fence only runs `touch` when `grep` finds `- **Cost**:` in `summary-final.md` (1751–1754). If the script exits 0 yet the file has no cost bullet (transient render bug, stale file, or partial write), the agent may assume Step 18 will not re-print while also skipping the collapse-resistant cost-line emit (1760 gates on the same condition). **Suggested fix:** Align NEVER #20 and the Step 17 orchestrator sub-step with the Bash guard—e.g. “touch `.step17-printed` only when `write-final-report.sh` succeeds and `summary-final.md` contains `- **Cost**:`”—or move the sentinel write into `write-final-report.sh` so script and SKILL prose share one contract.
- **Suggested revision**: Address the concern above.

### FINDING_26: **correctness** `skills/implement/SKILL.md:1762` — Step 17 failure handling still refers to `STATUS=failed` on a “script envelope,” but the Step 17 fence no longer uses `|| true` or parses `STATUS=ok`/`STATUS=failed` (branch diff removed the old `write-final-report.sh … || true` line). Failures are now plain non-zero exits from the `if …; then` wrapper. **Suggested fix:** Replace the STATUS-envelope paragraph with guidance that matches the current Bash shape (non-zero exit → log via `append-tool-failure.sh`, no sentinel, Step 18 may conditionally re-print), and drop references to `STATUS=skipped` here unless that KV is actually emitted on this callsite.
- **Reviewer**: dyn-skill-prose-consistency-output.txt
- **Concern**: - **correctness** `skills/implement/SKILL.md:1762` — Step 17 failure handling still refers to `STATUS=failed` on a “script envelope,” but the Step 17 fence no longer uses `|| true` or parses `STATUS=ok`/`STATUS=failed` (branch diff removed the old `write-final-report.sh … || true` line). Failures are now plain non-zero exits from the `if …; then` wrapper. **Suggested fix:** Replace the STATUS-envelope paragraph with guidance that matches the current Bash shape (non-zero exit → log via `append-tool-failure.sh`, no sentinel, Step 18 may conditionally re-print), and drop references to `STATUS=skipped` here unless that KV is actually emitted on this callsite.
- **Suggested revision**: Address the concern above.

### FINDING_27: **correctness** `scripts/test-render-cost-line-callsites.sh:35-38` — The Step 17 lint only checks the substring `write-final-report.sh" --implement-tmpdir "$IMPLEMENT_TMPDIR" --print-stdout; then` and its comment claims the sentinel is gated on “write-final-report success,” but SKILL.md also nests `grep -Fq -- '- **Cost**:'` before `touch` (1752–1753). Step 18’s cost-line gate is pinned (line 38); Step 17’s is not. The plan’s acceptance item 5 also called for greps of the full NEVER #20 literal, the design anti-recap rule, and the implement “emit one line … cost line verbatim” prose—none of those are in this harness. **Suggested fix:** Add `grep -Fq` assertions for the Step 17 cost-line guard, implement NEVER #20 / cost-emit substrings, and design anti-recap + post-publish emit prose so CI catches prose drift on the sentinel and ROOT CAUSE G contracts.
- **Reviewer**: dyn-skill-prose-consistency-output.txt
- **Concern**: - **correctness** `scripts/test-render-cost-line-callsites.sh:35-38` — The Step 17 lint only checks the substring `write-final-report.sh" --implement-tmpdir "$IMPLEMENT_TMPDIR" --print-stdout; then` and its comment claims the sentinel is gated on “write-final-report success,” but SKILL.md also nests `grep -Fq -- '- **Cost**:'` before `touch` (1752–1753). Step 18’s cost-line gate is pinned (line 38); Step 17’s is not. The plan’s acceptance item 5 also called for greps of the full NEVER #20 literal, the design anti-recap rule, and the implement “emit one line … cost line verbatim” prose—none of those are in this harness. **Suggested fix:** Add `grep -Fq` assertions for the Step 17 cost-line guard, implement NEVER #20 / cost-emit substrings, and design anti-recap + post-publish emit prose so CI catches prose drift on the sentinel and ROOT CAUSE G contracts.
- **Suggested revision**: Address the concern above.

### FINDING_28: **correctness** `skills/design/SKILL.md:1016-1020` — Step 5d says “the only orchestrator-text addition permitted after that Bash output is the single extracted `- **Cost**:` line,” but the next lines require repeating external-reviewer warnings (1020) and emitting the Step 5 machine footer (1022–1024) on the happy path. That is contradictory for Step 5c: an agent obeying 1016 literally may omit warnings/footer. **Suggested fix:** Rewrite 1016 to list permitted post-summary orchestrator output in order—verbatim cost line, then warning repeats, then the machine footer—and state that free-form recaps remain forbidden between those pieces.
- **Reviewer**: dyn-skill-prose-consistency-output.txt
- **Concern**: - **correctness** `skills/design/SKILL.md:1016-1020` — Step 5d says “the only orchestrator-text addition permitted after that Bash output is the single extracted `- **Cost**:` line,” but the next lines require repeating external-reviewer warnings (1020) and emitting the Step 5 machine footer (1022–1024) on the happy path. That is contradictory for Step 5c: an agent obeying 1016 literally may omit warnings/footer. **Suggested fix:** Rewrite 1016 to list permitted post-summary orchestrator output in order—verbatim cost line, then warning repeats, then the machine footer—and state that free-form recaps remain forbidden between those pieces.
- **Suggested revision**: Address the concern above.

### FINDING_29: [OUT_OF_SCOPE] The `grep -Fq` patterns in `test-render-cost-line-callsites.sh` do match the current SKILL.md text; the harness passes as written.
- **Reviewer**: dyn-skill-prose-consistency-output.txt
- **Concern**: - The `grep -Fq` patterns in `test-render-cost-line-callsites.sh` do match the current SKILL.md text; the harness passes as written.
- **Suggested revision**: Address the concern above.

### FINDING_30: [OUT_OF_SCOPE] `write-final-report.sh` Stage 2 self-compose always emits `- **Cost**: N/A` (e.g. `compose_self_fallback` at 399), so the Step 17/18 cost-line grep is expected to succeed whenever the script exits 0 after fallback; the main prose risk is agents misreading NEVER #20, not routine fallback bodies.
- **Reviewer**: dyn-skill-prose-consistency-output.txt
- **Concern**: - `write-final-report.sh` Stage 2 self-compose always emits `- **Cost**: N/A` (e.g. `compose_self_fallback` at 399), so the Step 17/18 cost-line grep is expected to succeed whenever the script exits 0 after fallback; the main prose risk is agents misreading NEVER #20, not routine fallback bodies.
- **Suggested revision**: Address the concern above.

### FINDING_31: [OUT_OF_SCOPE] Implement Step 17/18 orchestrator cost-line emit and Bash guards are internally consistent with each other; design cost-line emit prose (288, 977) does not gate on success/presence the way implement does—lower risk because `render-final-summary.sh` fallback also always writes a cost bullet.
- **Reviewer**: dyn-skill-prose-consistency-output.txt
- **Concern**: - Implement Step 17/18 orchestrator cost-line emit and Bash guards are internally consistent with each other; design cost-line emit prose (288, 977) does not gate on success/presence the way implement does—lower risk because `render-final-summary.sh` fallback also always writes a cost bullet.
- **Suggested revision**: Address the concern above.

