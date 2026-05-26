### FINDING_1: code-quality: skills/implement/scripts/step-7a.sh:58-378
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Round 2 should_skip_diagram_upsert misses most REASON_TOKEN values and does not match awk-polluted SKIP_REASON strings. A sanitizer reject with SKIP_REASON like br-in-participant-alias or pipe-in-node-label fence=… still runs tracking-issue-summary.sh, posting a placeholder despite step-7a.md promising upsert skip on sanitizer rejection; harness stubs use clean tokens so CI can pass. Set COMMENT_UPSERT_SKIP=true when gen_status=skipped and/or parse REASON_TOKEN to the first field; add harness cases with production-shaped SKIP_REASON strings.
- **Suggested revision**: Address the concern above.

### FINDING_2: correctness: skills/implement/scripts/step-7a.sh:376-378
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Sanitizer upsert suppression is incomplete relative to plan and sibling docs. Live /implement runs can publish larch:diagrams after sanitizer rejection on tokens not covered by the case list, contradicting Round 1 Decision 2. Same as finding 1: gate on STATUS=skipped from generate-code-flow-diagram.sh instead of substring heuristics.
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: skills/implement/scripts/step-7a.sh:143-232
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] run_log_flush inlines the full pre-bump batch table instead of reusing a shared helper. Future batch slug or ordering changes require editing step-7a.sh and refresh paths separately, increasing drift risk. Extract a shared pre-bump-log-flush.sh after landing and keep step-7a.sh as thin orchestration.
- **Suggested revision**: Address the concern above.

### FINDING_4: code-quality: skills/implement/scripts/step-7a.sh:410
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Mid-script set -e breaks the file's explicit rc-handling style. A later unguarded command inside run_log_flush could abort the script before emit_tail without the intended degraded KV tail. Remove set -e and keep set +e or rc=$? around fallible calls like the rest of the script.
- **Suggested revision**: Address the concern above.

### FINDING_5: code-quality: skills/implement/scripts/step-7a.sh:183-198
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Non-zero capture-session-transcript handling appears dead under the documented always-exit-0 contract. Maintainers may assume LOG_FLUSH_STATUS=degraded can trigger from transcript capture when it cannot. Remove the rc check or align helper docs and tests if non-zero exits become possible.
- **Suggested revision**: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] risk-integration: skills/implement/SKILL.md:main
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Pre-change Step 7a always upserted on sanitizer rejection; skip-upsert is a deliberate plan change. Not introduced by this branch's intent; only relevant when comparing to historical main behavior. No change required once in-scope sanitizer gating is fixed.
- **Suggested revision**: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] code-quality: docs/linting.md:150
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Harness inventory row undercounts test-step-7a cases versus the script. Readers expect 10 cases while the harness runs 15. Update the linting.md row to match test-step-7a.md.
- **Suggested revision**: Address the concern above.

### FINDING_8: correctness: skills/implement/scripts/step-7a.sh:58-63
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] should_skip_diagram_upsert omits several sanitizer REASON_TOKEN values br-in-participant-alias rejection still upserts larch:diagrams with placeholder while plan/harness assume sanitizer rejection skips upsert Match all sanitize-mermaid REASON_TOKEN values or treat any skipped diagram with REASON_TOKEN as no-upsert; add harness case
- **Suggested revision**: Address the concern above.

### FINDING_9: correctness: skills/implement/scripts/step-7a.sh:383-398
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Sanitizer path skips upsert but main always upserted; conflicts with byte-identical acceptance pipe-in-node-label rejection leaves stale GitHub comment instead of updated placeholder Clarify acceptance or restore always-upsert on sanitizer rejection
- **Suggested revision**: Address the concern above.

### FINDING_10: correctness: skills/implement/scripts/step-7a.sh:410
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] set -e enabled mid-script after header omits -e future unguarded flush command could exit before emit_tail Remove set -e or guard run_log_flush and emit_tail together
- **Suggested revision**: Address the concern above.

### FINDING_11: correctness: skills/implement/scripts/test-step-7a.sh:342
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Green-path bail-reason assert is substring-based could false-pass if argv tail leaked into output Use grep -Fx or exact-line match for empty STEP_7A_BAIL_REASON
- **Suggested revision**: Address the concern above.

### FINDING_12: risk-integration: scripts/test-implement-structure.sh:264-265
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Structural harness still requires Step 7a timing-ledger mark in generate-code-flow-diagram.sh after marks moved to step-7a.sh make lint test-harnesses-14 runs test-implement-structure and fails grep on every CI pass Repoint the pin to skills/implement/scripts/step-7a.sh or update the assertion to match the new ownership
- **Suggested revision**: Address the concern above.

### FINDING_13: risk-integration: skills/implement/scripts/test-step-7a.sh:80-91
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Green-path harness never sets ARCHITECTURE_DIAGRAM_FILE so architecture half of larch:diagrams comment is untested A refactor breaking cat of ARCHITECTURE_DIAGRAM_FILE ships with PASS=16 Add a fixture case with ARCHITECTURE_DIAGRAM_FILE set and assert summary-diagrams.md leading content
- **Suggested revision**: Address the concern above.

### FINDING_14: risk-integration: skills/implement/scripts/test-step-7a.sh:1290-1304
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No case stubs failing larch-log.sh write while expecting LOG_FLUSH_STATUS=ok Regression could mark flush degraded on write-best-effort failures contrary to plan Add stub write failure and assert LOG_FLUSH_STATUS=ok plus Tool Failures entry
- **Suggested revision**: Address the concern above.

### FINDING_15: risk-integration: docs/linting.md:150
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] docs/linting.md lists 10 test-step-7a cases but harness documents 16 Contributors may think rebase and crash paths are out of scope Sync docs/linting.md inventory with test-step-7a.md case list
- **Suggested revision**: Address the concern above.

### FINDING_16: risk-integration: skills/implement/scripts/test-step-7a.sh:373-374
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] COMMENT_URL assertions use substring COMMENT_URL= only Stale non-empty COMMENT_URL could pass diagram-rejected and upsert-failure cases Assert exact COMMENT_URL= empty line on those paths
- **Suggested revision**: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] risk-integration: skills/implement/scripts/test-generate-code-flow-diagram.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Direct generator harness no longer hits Step 7a timing marks after consolidation Isolated generator runs omit timing telemetry unless called via step-7a.sh Only relevant if non-implement callers invoke the generator directly
- **Suggested revision**: Address the concern above.

### FINDING_18: correctness: skills/implement/scripts/step-7a.sh:10,183-198
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Outer larch_quiet_init hides capture-session-transcript SESSION_TRANSCRIPT_STATUS from Bash tool stdout. After consolidation the orchestrator no longer sees SESSION_TRANSCRIPT_STATUS on combined stdout; debugging and any prompt-side parsing of that line break vs main inline Step 7a. Run capture with LARCH_QUIET_DISABLE=1 or re-emit SESSION_TRANSCRIPT_STATUS to FD 3; add harness coverage.
- **Suggested revision**: Address the concern above.

### FINDING_19: correctness: skills/implement/scripts/step-7a.sh:58-63,376-378
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] should_skip_diagram_upsert omits several sanitizer REASON_TOKEN values. When sanitize rejects with br-in-participant-alias dollar-in-participant-alias or unclosed-frontmatter step-7a still upserts a misleading larch:diagrams placeholder comment. Match all REASON_TOKEN literals from sanitize-mermaid-fragment.sh or skip upsert on all STATUS=skipped from generator; extend tests.
- **Suggested revision**: Address the concern above.

### FINDING_20: risk-integration: skills/implement/scripts/step-7a.sh:40-50,195-198
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] append-tool-failure.sh output is discarded so execution-issues.md may stay empty on failures. Flush or diagram failures can leave no Tool Failures or Warnings entries while KV tail shows degraded or exit 0. Stop redirecting append-tool-failure to /dev/null; record append failures in KV or stderr.
- **Suggested revision**: Address the concern above.

### FINDING_21: correctness: skills/implement/scripts/step-7a.sh:195-198
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] capture-session-transcript rc check is dead because the helper always exits 0. Future capture behavior changes will not flip LOG_FLUSH_STATUS via rc; maintainers may assume rc-based handling exists. Remove dead rc branch or degrade based on SESSION_TRANSCRIPT_STATUS parsing.
- **Suggested revision**: Address the concern above.

### FINDING_22: code-quality: skills/implement/scripts/step-7a.sh:410,126-137
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] set -e after rebase is cleared by set +e inside run_larch_log_write. Post-rebase errexit does not protect flush or emit_tail as intended. Save/restore errexit around run_larch_log_write or avoid global set +e in the function.
- **Suggested revision**: Address the concern above.

### FINDING_23: correctness: skills/implement/scripts/step-7a.sh:58-63
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] *reject* glob in should_skip_diagram_upsert is overly broad. A future SKIP_REASON containing reject could suppress larch:diagrams upsert without posting any comment. Use explicit REASON_TOKEN list instead of *reject* substring match.
- **Suggested revision**: Address the concern above.

### FINDING_24: [OUT_OF_SCOPE] code-quality: docs/linting.md
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Harness inventory understates test-step-7a case count. Docs claim 10 cases while harness runs 16. Update linting.md inventory row.
- **Suggested revision**: Address the concern above.

### FINDING_25: [OUT_OF_SCOPE] correctness: skills/implement/scripts/step-7a.sh:88
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Classifier always uses origin/main not upstream in forked mode. Fork repos without origin/main never get small/non-runtime skip. Pre-existing; align classifier remote with forked_target if desired later.
- **Suggested revision**: Address the concern above.

### FINDING_26: correctness: skills/implement/scripts/step-7a.sh:58-62,376-399
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Sanitizer rejection skips larch:diagrams upsert but main SKILL always upserted placeholder comment STATUS=skipped with sanitizer SKIP_REASON leaves tracking issue without updated larch:diagrams comment that main would post with Code flow diagram not available Restore upsert on sanitizer path for byte-identical behavior or revise acceptance and document intentional skip-upsert
- **Suggested revision**: Address the concern above.

### FINDING_27: correctness: skills/implement/scripts/step-7a.sh:407-418
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Rebase failure exits 1/3 and skips pre-bump flush contrary to plan section 12 exit 0 After rebase conflict callers following issue plan expect flush to run; step-7a exits early and LOG_FLUSH_STATUS=skipped-rebase-checkpoint Update larch:plan to match step-7a.md/SKILL.md or change script to exit 0 and handle conflict only in macro prose
- **Suggested revision**: Address the concern above.

### FINDING_28: architecture: skills/implement/scripts/step-7a.sh:407-414
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Rebase probe stdout captured to file and re-emitted instead of FD3 inheritance per plan Probe diagnostics emitted only on FD3 could be lost before orchestrator macro routing Document capture-relay as canonical or stop redirecting probe stdout
- **Suggested revision**: Address the concern above.

### FINDING_29: correctness: skills/implement/scripts/step-7a.sh:410
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] set -e enabled after successful rebase contradicts plan non-e bootstrap Unguarded post-rebase failure may abort with undocumented non-zero exit instead of degraded KV tail Remove set -e or keep set +e through final exit 0
- **Suggested revision**: Address the concern above.

### FINDING_30: **correctness** `skills/implement/scripts/step-7a.sh:410-422` — The script deliberately omits `-e` at the top (`set -uo pipefail`, line 4) so child failures are handled via explicit `rc` checks and `append-tool-failure.sh`, but line 410 turns errexit on for the rebase KV re-emit loop and never restores it before the tail. `run_log_flush` (line 421) immediately executes `set +e` (line 151), which disables errexit for the rest of the process; `emit_tail` (line 422) therefore runs with errexit off. Net effect: a failing `emit` in the `while read` loop (lines 411–414) can abort the script **before** pre-bump flush, while failures in the final KV tail are silently ignored—opposite halves of an inconsistent policy. **Suggested fix:** Drop the mid-script `set -e` (keep the planned no-`-e` orchestration model) and handle re-emit failures explicitly if needed; if errexit is truly required for that loop, wrap only that loop and run `set +e` (or restore the prior option state) before calling `run_log_flush` / `emit_tail`.
- **Reviewer**: dyn-shell-mode-flags-output.txt
- **Concern**: - **correctness** `skills/implement/scripts/step-7a.sh:410-422` — The script deliberately omits `-e` at the top (`set -uo pipefail`, line 4) so child failures are handled via explicit `rc` checks and `append-tool-failure.sh`, but line 410 turns errexit on for the rebase KV re-emit loop and never restores it before the tail. `run_log_flush` (line 421) immediately executes `set +e` (line 151), which disables errexit for the rest of the process; `emit_tail` (line 422) therefore runs with errexit off. Net effect: a failing `emit` in the `while read` loop (lines 411–414) can abort the script **before** pre-bump flush, while failures in the final KV tail are silently ignored—opposite halves of an inconsistent policy. **Suggested fix:** Drop the mid-script `set -e` (keep the planned no-`-e` orchestration model) and handle re-emit failures explicitly if needed; if errexit is truly required for that loop, wrap only that loop and run `set +e` (or restore the prior option state) before calling `run_log_flush` / `emit_tail`.
- **Suggested revision**: Address the concern above.

### FINDING_31: **correctness** `skills/implement/scripts/step-7a.sh:129-137,151-157,173-176,184-194,201-210,218-224,346-349,386-392` — Every guarded block uses `set +e` before the command and `set +e` again after `rc=$?` instead of the repo’s usual `set +e` / `set -e` pair (see `skills/implement/scripts/oos-disposition-gate.sh:48-51` and `skills/implement/scripts/test-step-7a.sh:333-336`). In Bash, `set` inside a function mutates the caller’s option state; these blocks never re-enable errexit. That is mostly harmless while the script stays without `-e`, but it amplifies the bug above once line 410 enables `-e`, and it is a footgun for any later edit that adds top-level `-e`. **Suggested fix:** Replace the second `set +e` in each pair with `set -e` when restoring a prior `-e` session, or remove the toggles entirely and rely on `rc=$?` plus `|| true` / explicit failure routing, matching `flush-execution-issues.sh`’s top-level style without introducing mid-script `-e`.
- **Reviewer**: dyn-shell-mode-flags-output.txt
- **Concern**: - **correctness** `skills/implement/scripts/step-7a.sh:129-137,151-157,173-176,184-194,201-210,218-224,346-349,386-392` — Every guarded block uses `set +e` before the command and `set +e` again after `rc=$?` instead of the repo’s usual `set +e` / `set -e` pair (see `skills/implement/scripts/oos-disposition-gate.sh:48-51` and `skills/implement/scripts/test-step-7a.sh:333-336`). In Bash, `set` inside a function mutates the caller’s option state; these blocks never re-enable errexit. That is mostly harmless while the script stays without `-e`, but it amplifies the bug above once line 410 enables `-e`, and it is a footgun for any later edit that adds top-level `-e`. **Suggested fix:** Replace the second `set +e` in each pair with `set -e` when restoring a prior `-e` session, or remove the toggles entirely and rely on `rc=$?` plus `|| true` / explicit failure routing, matching `flush-execution-issues.sh`’s top-level style without introducing mid-script `-e`.
- **Suggested revision**: Address the concern above.

### FINDING_32: [OUT_OF_SCOPE] correctness
- **Reviewer**: dyn-shell-mode-flags-output.txt
- **Concern**: - **correctness** `skills/implement/scripts/flush-execution-issues.sh:170-179` — The same `set +e` / `set +e` pattern exists pre-branch; `step-7a.sh` copied it. Worth aligning both when fixing `step-7a.sh`, but not introduced solely by this branch’s new logic beyond mirroring.
- **Suggested revision**: Address the concern above.

### FINDING_33: [OUT_OF_SCOPE] correctness
- **Reviewer**: dyn-shell-mode-flags-output.txt
- **Concern**: - **correctness** `scripts/lint-foreground-markers.sh:115-158,349-361` — New `foreground_banner_ok_in_window` / `foreground_comment_ok_before_anchor_idx` duplicate existing constructs (`[[`, `local -a`, `(( ))`) already used throughout the file; `lint-bash32.sh` does not flag them, and no Bash 4-only features (`declare -A`, `mapfile`, `${var^^}`, `&>>`) were added in the branch diff for this file.
- **Suggested revision**: Address the concern above.

### FINDING_34: **architecture** `skills/implement/SKILL.md:123-134` — The canonical **Rebase Checkpoint Macro** still tells the orchestrator to “Run the foreground `rebase-checkpoint-probe.sh` invocation” and treats every registry row (including `7a.r`) as a direct probe Bash call, but Step 7a now runs a single `step-7a.sh` wrapper. Step 7a prose at `1434` correctly says to apply macro routing after `step-7a.sh` returns and that the helper preserves the probe exit code, yet the Macro section never states that for `7a.r` the **process exit code to branch on is `step-7a.sh`’s exit** (1/3 on conflict/failure), not a standalone probe fence. That split contract makes KV-only routing (`REBASE_OUTCOME` parsing without honoring non-zero Bash exit) more likely and undermines the deliberate propagation in `skills/implement/scripts/step-7a.sh:415-418`. **Suggested fix:** Add a `7a.r` call-site exception in `## Rebase Checkpoint Macro` (registry note + orchestrator step 1) stating that `7a.r` is reached via `step-7a.sh`, macro routing must use the wrapper’s combined stdout **and** its process exit code, and pre-bump flush only occurs inside the helper when `REBASE_OUTCOME=ok|skipped`.
- **Reviewer**: dyn-rebase-exit-propagation-output.txt
- **Concern**: - **architecture** `skills/implement/SKILL.md:123-134` — The canonical **Rebase Checkpoint Macro** still tells the orchestrator to “Run the foreground `rebase-checkpoint-probe.sh` invocation” and treats every registry row (including `7a.r`) as a direct probe Bash call, but Step 7a now runs a single `step-7a.sh` wrapper. Step 7a prose at `1434` correctly says to apply macro routing after `step-7a.sh` returns and that the helper preserves the probe exit code, yet the Macro section never states that for `7a.r` the **process exit code to branch on is `step-7a.sh`’s exit** (1/3 on conflict/failure), not a standalone probe fence. That split contract makes KV-only routing (`REBASE_OUTCOME` parsing without honoring non-zero Bash exit) more likely and undermines the deliberate propagation in `skills/implement/scripts/step-7a.sh:415-418`. **Suggested fix:** Add a `7a.r` call-site exception in `## Rebase Checkpoint Macro` (registry note + orchestrator step 1) stating that `7a.r` is reached via `step-7a.sh`, macro routing must use the wrapper’s combined stdout **and** its process exit code, and pre-bump flush only occurs inside the helper when `REBASE_OUTCOME=ok|skipped`.
- **Suggested revision**: Address the concern above.

### FINDING_35: **architecture** `scripts/test-implement-rebase-macro.sh:63-77` — The macro pin harness still requires exactly four literal `"${CLAUDE_PLUGIN_ROOT}/scripts/rebase-checkpoint-probe.sh"` invocations in `SKILL.md`, including `rebase-checkpoint-probe.sh" 7a.r`, but the branch removes the Step 7a probe fence and leaves only three SKILL-level probe calls (`1.r`, `4.r`, `7.r`). `make test-implement-rebase-macro` fails with `(C) expected exactly 4 … found 3`, so the consolidated 7a architecture is not reflected in the repo’s structural guard for rebase checkpoints. **Suggested fix:** Update `test-implement-rebase-macro.sh` to expect three direct SKILL invocations plus a `step-7a.sh` invocation (or `step-7a.sh` containing `7a.r`), and align the Macro “thin implementation” bullet so it no longer claims all four sites are direct probe fences.
- **Reviewer**: dyn-rebase-exit-propagation-output.txt
- **Concern**: - **architecture** `scripts/test-implement-rebase-macro.sh:63-77` — The macro pin harness still requires exactly four literal `"${CLAUDE_PLUGIN_ROOT}/scripts/rebase-checkpoint-probe.sh"` invocations in `SKILL.md`, including `rebase-checkpoint-probe.sh" 7a.r`, but the branch removes the Step 7a probe fence and leaves only three SKILL-level probe calls (`1.r`, `4.r`, `7.r`). `make test-implement-rebase-macro` fails with `(C) expected exactly 4 … found 3`, so the consolidated 7a architecture is not reflected in the repo’s structural guard for rebase checkpoints. **Suggested fix:** Update `test-implement-rebase-macro.sh` to expect three direct SKILL invocations plus a `step-7a.sh` invocation (or `step-7a.sh` containing `7a.r`), and align the Macro “thin implementation” bullet so it no longer claims all four sites are direct probe fences.
- **Suggested revision**: Address the concern above.

### FINDING_36: **architecture** `skills/implement/scripts/step-7a.sh:415-418` vs embedded plan in `larch-logs/` — The implementation intentionally diverges from the issue plan’s “exit 0 except argv” contract by propagating rebase probe exits (`exit "$rebase_rc"`) and emitting `LOG_FLUSH_STATUS=skipped-rebase-checkpoint` before early exit; `step-7a.md:30-37` and `SKILL.md:1434` document that behavior, which matches pre-consolidation semantics (standalone probe returned 1/3 to the orchestrator). This is not a runtime regression, but the stale plan/acceptance text still claims exit-0-always and omits `skipped-rebase-checkpoint`, which can mislead reviewers and implementers into “fixing” the propagation back to exit 0. **Suggested fix:** Treat propagation as canonical; update the issue plan / `larch:plan` acceptance bullets to document exits `1`/`3`, `LOG_FLUSH_STATUS=skipped-rebase-checkpoint`, and that macro routing consumes `step-7a.sh`’s process exit code—not a wrapper that always returns 0.
- **Reviewer**: dyn-rebase-exit-propagation-output.txt
- **Concern**: - **architecture** `skills/implement/scripts/step-7a.sh:415-418` vs embedded plan in `larch-logs/` — The implementation intentionally diverges from the issue plan’s “exit 0 except argv” contract by propagating rebase probe exits (`exit "$rebase_rc"`) and emitting `LOG_FLUSH_STATUS=skipped-rebase-checkpoint` before early exit; `step-7a.md:30-37` and `SKILL.md:1434` document that behavior, which matches pre-consolidation semantics (standalone probe returned 1/3 to the orchestrator). This is not a runtime regression, but the stale plan/acceptance text still claims exit-0-always and omits `skipped-rebase-checkpoint`, which can mislead reviewers and implementers into “fixing” the propagation back to exit 0. **Suggested fix:** Treat propagation as canonical; update the issue plan / `larch:plan` acceptance bullets to document exits `1`/`3`, `LOG_FLUSH_STATUS=skipped-rebase-checkpoint`, and that macro routing consumes `step-7a.sh`’s process exit code—not a wrapper that always returns 0.
- **Suggested revision**: Address the concern above.

### FINDING_37: [OUT_OF_SCOPE] architecture
- **Reviewer**: dyn-rebase-exit-propagation-output.txt
- **Concern**: - **architecture** `skills/implement/SKILL.md:1436` — The unqualified `> **Continue to Step 8 IMMEDIATELY.**` blockquote sits immediately after macro-routing instructions; on rebase conflict/failure the Macro bail branches skip to conflict resolution or Step 18, not Step 8. This ordering predates the consolidation (same pattern at Step 4.r → Step 5) and was not introduced solely by `step-7a.sh`, though the single-call Step 7a shape makes the tension slightly sharper.
- **Suggested revision**: Address the concern above.

### FINDING_38: [OUT_OF_SCOPE] Propagating rebase exits from inside `step-7a.sh` is **architecturally sound** relative to the old two-fence flow: pre-bump flush is correctly skipped on non-zero rebase (`test-step-7a.sh` `rebase-conflict` / `rebase-failed`), and `LOG_FLUSH_STATUS=skipped-rebase-checkpoint` is documented in `step-7a.md:25` even though `SKILL.md:1442` tells the orchestrator not to parse that KV for routing (macro exit-code routing remains the authority).
- **Reviewer**: dyn-rebase-exit-propagation-output.txt
- **Concern**: - Propagating rebase exits from inside `step-7a.sh` is **architecturally sound** relative to the old two-fence flow: pre-bump flush is correctly skipped on non-zero rebase (`test-step-7a.sh` `rebase-conflict` / `rebase-failed`), and `LOG_FLUSH_STATUS=skipped-rebase-checkpoint` is documented in `step-7a.md:25` even though `SKILL.md:1442` tells the orchestrator not to parse that KV for routing (macro exit-code routing remains the authority).
- **Suggested revision**: Address the concern above.

### FINDING_39: **architecture** `skills/implement/scripts/step-7a.sh:407-414` — Redirecting `rebase-checkpoint-probe.sh` stdout to `$rebase_out` and re-emitting with `emit "$line"` is the correct relay under `larch_quiet_init`, not a regression versus “natural FD 3 inheritance.” After quiet init, the probe child’s `emit`/`emit_kv` calls go to the child’s stdout (because `LARCH_QUIET_PID` is the parent’s PID, not the child’s `$$` per `scripts/lib-quiet.sh:112-117`); without capture, those KVs would land on the parent’s redirected FD 1 (quiet log) and would not reach the orchestrator’s contract stream (FD 3). Re-emission via `emit` routes relayed lines back to FD 3 the same way `scripts/test-lib-quiet.sh:40-45` proves contract output remains visible under command substitution. **Suggested fix:** Keep capture+re-emit; update any remaining plan prose that still claims FD 3 inheritance (the embedded plan in the issue block still says that) so maintainers do not “simplify” this away. Optionally filter re-emission to `KEY=value` lines only if breadcrumb prose on the contract stream is undesirable—today `LARCH_QUIET_BREADCRUMBS=1` without `LARCH_QUIET_BREADCRUMB_FD` will also forward `→ rebase-probe: …` lines, matching direct probe fences.
- **Reviewer**: dyn-quiet-stream-contract-output.txt
- **Concern**: - **architecture** `skills/implement/scripts/step-7a.sh:407-414` — Redirecting `rebase-checkpoint-probe.sh` stdout to `$rebase_out` and re-emitting with `emit "$line"` is the correct relay under `larch_quiet_init`, not a regression versus “natural FD 3 inheritance.” After quiet init, the probe child’s `emit`/`emit_kv` calls go to the child’s stdout (because `LARCH_QUIET_PID` is the parent’s PID, not the child’s `$$` per `scripts/lib-quiet.sh:112-117`); without capture, those KVs would land on the parent’s redirected FD 1 (quiet log) and would not reach the orchestrator’s contract stream (FD 3). Re-emission via `emit` routes relayed lines back to FD 3 the same way `scripts/test-lib-quiet.sh:40-45` proves contract output remains visible under command substitution. **Suggested fix:** Keep capture+re-emit; update any remaining plan prose that still claims FD 3 inheritance (the embedded plan in the issue block still says that) so maintainers do not “simplify” this away. Optionally filter re-emission to `KEY=value` lines only if breadcrumb prose on the contract stream is undesirable—today `LARCH_QUIET_BREADCRUMBS=1` without `LARCH_QUIET_BREADCRUMB_FD` will also forward `→ rebase-probe: …` lines, matching direct probe fences.
- **Suggested revision**: Address the concern above.

### FINDING_40: **architecture** `skills/implement/scripts/test-step-7a.sh:486-493` — `quiet-rebase-contract` is the only case that unsets `LARCH_QUIET_DISABLE` (production quiet path via `run_helper_quiet:295-305`), but it still stubs `rebase-checkpoint-probe.sh` with bare `printf` lines (`test-step-7a.sh:161-177`) instead of exercising the real probe’s `emit_kv` + `phantom_probe_with_warn` tail (`PHANTOM_*` keys documented in `scripts/rebase-checkpoint-probe.md:33-33`). The case therefore validates quiet re-emission mechanics for `REBASE_OUTCOME=ok` only, not the full production envelope the Rebase Checkpoint Macro must parse after Step 7a consolidation. **Suggested fix:** Add a harness case (or extend `quiet-rebase-contract`) that invokes the real `scripts/rebase-checkpoint-probe.sh` against the existing `test-rebase-checkpoint-probe.sh` stub tree under quiet mode, and assert `REBASE_OUTCOME`, at least one `PHANTOM_*` line, and ordering (probe KVs before `DIAGRAM_STATUS=` tail) on the captured contract stream.
- **Reviewer**: dyn-quiet-stream-contract-output.txt
- **Concern**: - **architecture** `skills/implement/scripts/test-step-7a.sh:486-493` — `quiet-rebase-contract` is the only case that unsets `LARCH_QUIET_DISABLE` (production quiet path via `run_helper_quiet:295-305`), but it still stubs `rebase-checkpoint-probe.sh` with bare `printf` lines (`test-step-7a.sh:161-177`) instead of exercising the real probe’s `emit_kv` + `phantom_probe_with_warn` tail (`PHANTOM_*` keys documented in `scripts/rebase-checkpoint-probe.md:33-33`). The case therefore validates quiet re-emission mechanics for `REBASE_OUTCOME=ok` only, not the full production envelope the Rebase Checkpoint Macro must parse after Step 7a consolidation. **Suggested fix:** Add a harness case (or extend `quiet-rebase-contract`) that invokes the real `scripts/rebase-checkpoint-probe.sh` against the existing `test-rebase-checkpoint-probe.sh` stub tree under quiet mode, and assert `REBASE_OUTCOME`, at least one `PHANTOM_*` line, and ordering (probe KVs before `DIAGRAM_STATUS=` tail) on the captured contract stream.
- **Suggested revision**: Address the concern above.

### FINDING_41: [OUT_OF_SCOPE] `scripts/test-implement-rebase-macro.sh:63-77` still requires four literal `"${CLAUDE_PLUGIN_ROOT}/scripts/rebase-checkpoint-probe.sh"` invocations in `skills/implement/SKILL.md`, including `7a.r`, but the branch moved 7a.r into `step-7a.sh` (SKILL now has three direct probe fences). That structural test likely fails `make lint` until updated to accept the delegated `step-7a.sh` call site.
- **Reviewer**: dyn-quiet-stream-contract-output.txt
- **Concern**: - `scripts/test-implement-rebase-macro.sh:63-77` still requires four literal `"${CLAUDE_PLUGIN_ROOT}/scripts/rebase-checkpoint-probe.sh"` invocations in `skills/implement/SKILL.md`, including `7a.r`, but the branch moved 7a.r into `step-7a.sh` (SKILL now has three direct probe fences). That structural test likely fails `make lint` until updated to accept the delegated `step-7a.sh` call site.
- **Suggested revision**: Address the concern above.

### FINDING_42: [OUT_OF_SCOPE] `skills/implement/scripts/step-7a.sh:185-192` runs `capture-session-transcript.sh` without stdout suppression while `larch_quiet_init` is active at `step-7a.sh:10`; machine `SESSION_TRANSCRIPT_STATUS=` lines now go to the quiet log (FD 1), not the caller-visible contract stream, whereas the removed inline Step 7a fence exposed them on bash stdout. SKILL prose says the orchestrator does not parse flush KVs, so impact is likely telemetry-only.
- **Reviewer**: dyn-quiet-stream-contract-output.txt
- **Concern**: - `skills/implement/scripts/step-7a.sh:185-192` runs `capture-session-transcript.sh` without stdout suppression while `larch_quiet_init` is active at `step-7a.sh:10`; machine `SESSION_TRANSCRIPT_STATUS=` lines now go to the quiet log (FD 1), not the caller-visible contract stream, whereas the removed inline Step 7a fence exposed them on bash stdout. SKILL prose says the orchestrator does not parse flush KVs, so impact is likely telemetry-only.
- **Suggested revision**: Address the concern above.

### FINDING_43: **correctness** `skills/implement/scripts/step-7a.sh:58-62` — `should_skip_diagram_upsert` only suppresses the `larch:diagrams` upsert for `pipe-in-node-label`, `sanitizer-*`, `*sanitiz*`, and `*reject*`. Production sanitizer rejection flows through `generate-code-flow-diagram.sh:99-102`, which always emits `STATUS=skipped` with `SKIP_REASON` taken from the first `REASON_TOKEN` in the sanitizer log (`scripts/sanitize-mermaid-fragment.sh:201-238`). Three of the four real tokens (`br-in-participant-alias`, `dollar-in-participant-alias`, `unclosed-frontmatter`) match none of those patterns, so Step 7a still composes `summary-diagrams.md` and calls `tracking-issue-summary.sh` for those rejections. That contradicts `step-7a.md:48` (“Sanitizer rejection suppresses the `larch:diagrams` upsert”) and leaves skip-upsert behavior dependent on which sanitizer rule fired. **Suggested fix:** Treat `STATUS=skipped` from `generate-code-flow-diagram.sh` as the sanitizer-rejection signal (that script has no other `skipped` exit today), or enumerate every `REASON_TOKEN` from `scripts/sanitize-mermaid-fragment.sh:201-238` explicitly; add harness cases for each token so regressions cannot hide behind the `pipe-in-node-label`-only stub.
- **Reviewer**: dyn-sanitizer-rejection-semantics-output.txt
- **Concern**: - **correctness** `skills/implement/scripts/step-7a.sh:58-62` — `should_skip_diagram_upsert` only suppresses the `larch:diagrams` upsert for `pipe-in-node-label`, `sanitizer-*`, `*sanitiz*`, and `*reject*`. Production sanitizer rejection flows through `generate-code-flow-diagram.sh:99-102`, which always emits `STATUS=skipped` with `SKIP_REASON` taken from the first `REASON_TOKEN` in the sanitizer log (`scripts/sanitize-mermaid-fragment.sh:201-238`). Three of the four real tokens (`br-in-participant-alias`, `dollar-in-participant-alias`, `unclosed-frontmatter`) match none of those patterns, so Step 7a still composes `summary-diagrams.md` and calls `tracking-issue-summary.sh` for those rejections. That contradicts `step-7a.md:48` (“Sanitizer rejection suppresses the `larch:diagrams` upsert”) and leaves skip-upsert behavior dependent on which sanitizer rule fired. **Suggested fix:** Treat `STATUS=skipped` from `generate-code-flow-diagram.sh` as the sanitizer-rejection signal (that script has no other `skipped` exit today), or enumerate every `REASON_TOKEN` from `scripts/sanitize-mermaid-fragment.sh:201-238` explicitly; add harness cases for each token so regressions cannot hide behind the `pipe-in-node-label`-only stub.
- **Suggested revision**: Address the concern above.

### FINDING_44: **correctness** `skills/implement/scripts/step-7a.sh:358-377` — Even for tokens that do match `should_skip_diagram_upsert`, suppressing the upsert is a behavior change relative to `main` `skills/implement/SKILL.md` (removed lines in the branch diff around the old Step 7a block): main always posted the `larch:diagrams` comment with the `"Code flow diagram not available."` placeholder on sanitizer rejection and only logged a warning when `STATUS=failed`. The branch now skips upsert for some sanitizer paths but not others (see finding above), so acceptance text claiming a preserved “sanitizer-rejection skip path” and “byte-identical” comment output is only partially true. **Suggested fix:** Decide explicitly whether skip-upsert is the intended product change; if yes, skip for all sanitizer `STATUS=skipped` outcomes and document the divergence from main in `step-7a.md` / `SKILL.md`; if no, remove `COMMENT_UPSERT_SKIP` and restore unconditional upsert to match main.
- **Reviewer**: dyn-sanitizer-rejection-semantics-output.txt
- **Concern**: - **correctness** `skills/implement/scripts/step-7a.sh:358-377` — Even for tokens that do match `should_skip_diagram_upsert`, suppressing the upsert is a behavior change relative to `main` `skills/implement/SKILL.md` (removed lines in the branch diff around the old Step 7a block): main always posted the `larch:diagrams` comment with the `"Code flow diagram not available."` placeholder on sanitizer rejection and only logged a warning when `STATUS=failed`. The branch now skips upsert for some sanitizer paths but not others (see finding above), so acceptance text claiming a preserved “sanitizer-rejection skip path” and “byte-identical” comment output is only partially true. **Suggested fix:** Decide explicitly whether skip-upsert is the intended product change; if yes, skip for all sanitizer `STATUS=skipped` outcomes and document the divergence from main in `step-7a.md` / `SKILL.md`; if no, remove `COMMENT_UPSERT_SKIP` and restore unconditional upsert to match main.
- **Suggested revision**: Address the concern above.

### FINDING_45: **correctness** `skills/implement/scripts/step-7a.sh:60` — The `*reject*` case-arm matches any `SKIP_REASON` containing the substring `reject`, not only sanitizer failures. Current generator failure tokens (`generation-failed`, `empty-generation`, etc. in `generate-code-flow-diagram.sh:43-84`) do not hit this today, but a future reason like `model-rejected-output` on `STATUS=failed` would suppress upsert while still taking the `failed` branch and appending a Warning—silently diverging from the “post placeholder comment on generation failure” contract. **Suggested fix:** Drop the broad `*reject*` glob; key off `STATUS=skipped` from the diagram generator and/or the closed `REASON_TOKEN` set from `sanitize-mermaid-fragment.sh` instead of substring heuristics.
- **Reviewer**: dyn-sanitizer-rejection-semantics-output.txt
- **Concern**: - **correctness** `skills/implement/scripts/step-7a.sh:60` — The `*reject*` case-arm matches any `SKIP_REASON` containing the substring `reject`, not only sanitizer failures. Current generator failure tokens (`generation-failed`, `empty-generation`, etc. in `generate-code-flow-diagram.sh:43-84`) do not hit this today, but a future reason like `model-rejected-output` on `STATUS=failed` would suppress upsert while still taking the `failed` branch and appending a Warning—silently diverging from the “post placeholder comment on generation failure” contract. **Suggested fix:** Drop the broad `*reject*` glob; key off `STATUS=skipped` from the diagram generator and/or the closed `REASON_TOKEN` set from `sanitize-mermaid-fragment.sh` instead of substring heuristics.
- **Suggested revision**: Address the concern above.

### FINDING_46: **correctness** `skills/implement/scripts/test-step-7a.sh:122-125,365-375` — The `diagram-rejected` case correctly models production (`STATUS=skipped`, `SKIP_REASON=pipe-in-node-label`) rather than the plan’s synthetic `STATUS=failed` / `sanitizer-rejected` pair, but it only exercises one of four sanitizer tokens and therefore would not catch the incomplete `should_skip_diagram_upsert` list. The harness also asserts no Warning for sanitizer rejection, which aligns with production (`generate-code-flow-diagram.sh` exits 0 on sanitizer skip) but differs from the plan’s “failed + warning” expectation. **Suggested fix:** Add one harness case per `REASON_TOKEN` (or a parameterized loop) asserting `tracking-issue-summary.sh` is absent from `calls.log` and `COMMENT_URL` is empty; keep `diagram-skipped-non-sanitizer` only if the generator contract gains a real non-sanitizer `STATUS=skipped` path.
- **Reviewer**: dyn-sanitizer-rejection-semantics-output.txt
- **Concern**: - **correctness** `skills/implement/scripts/test-step-7a.sh:122-125,365-375` — The `diagram-rejected` case correctly models production (`STATUS=skipped`, `SKIP_REASON=pipe-in-node-label`) rather than the plan’s synthetic `STATUS=failed` / `sanitizer-rejected` pair, but it only exercises one of four sanitizer tokens and therefore would not catch the incomplete `should_skip_diagram_upsert` list. The harness also asserts no Warning for sanitizer rejection, which aligns with production (`generate-code-flow-diagram.sh` exits 0 on sanitizer skip) but differs from the plan’s “failed + warning” expectation. **Suggested fix:** Add one harness case per `REASON_TOKEN` (or a parameterized loop) asserting `tracking-issue-summary.sh` is absent from `calls.log` and `COMMENT_URL` is empty; keep `diagram-skipped-non-sanitizer` only if the generator contract gains a real non-sanitizer `STATUS=skipped` path.
- **Suggested revision**: Address the concern above.

### FINDING_47: [OUT_OF_SCOPE] Production `generate-code-flow-diagram.sh:99-102` emits `STATUS=skipped` (not `STATUS=failed`) for all sanitizer rejections; the round-2 implementation and test stub align with that, which is an improvement over the original plan text still embedded in `larch-logs/implement/.../plan-goals-test.md` and the diff’s plan appendix (`STATUS=failed`, `SKIP_REASON=sanitizer-rejected`).
- **Reviewer**: dyn-sanitizer-rejection-semantics-output.txt
- **Concern**: - Production `generate-code-flow-diagram.sh:99-102` emits `STATUS=skipped` (not `STATUS=failed`) for all sanitizer rejections; the round-2 implementation and test stub align with that, which is an improvement over the original plan text still embedded in `larch-logs/implement/.../plan-goals-test.md` and the diff’s plan appendix (`STATUS=failed`, `SKIP_REASON=sanitizer-rejected`).
- **Suggested revision**: Address the concern above.

### FINDING_48: [OUT_OF_SCOPE] Design-phase findings in `larch-logs/design/DD4D3283-21F1-455D-B7F0-10884E349CA7/findings.md` already flagged the token-contract mismatch; round 2 added `pipe-in-node-label` and updated the test stub but did not close the gap for the other three `REASON_TOKEN` values.
- **Reviewer**: dyn-sanitizer-rejection-semantics-output.txt
- **Concern**: - Design-phase findings in `larch-logs/design/DD4D3283-21F1-455D-B7F0-10884E349CA7/findings.md` already flagged the token-contract mismatch; round 2 added `pipe-in-node-label` and updated the test stub but did not close the gap for the other three `REASON_TOKEN` values.
- **Suggested revision**: Address the concern above.

