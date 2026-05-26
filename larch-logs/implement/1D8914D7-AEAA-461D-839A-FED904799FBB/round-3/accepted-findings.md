### FINDING_1: code-quality: skills/implement/scripts/step-7a.sh:58-378
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Round 2 should_skip_diagram_upsert misses most REASON_TOKEN values and does not match awk-polluted SKIP_REASON strings. A sanitizer reject with SKIP_REASON like br-in-participant-alias or pipe-in-node-label fence=… still runs tracking-issue-summary.sh, posting a placeholder despite step-7a.md promising upsert skip on sanitizer rejection; harness stubs use clean tokens so CI can pass. Set COMMENT_UPSERT_SKIP=true when gen_status=skipped and/or parse REASON_TOKEN to the first field; add harness cases with production-shaped SKIP_REASON strings.
- **Suggested revision**: Address the concern above.


### FINDING_10: correctness: skills/implement/scripts/step-7a.sh:410
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] set -e enabled mid-script after header omits -e future unguarded flush command could exit before emit_tail Remove set -e or guard run_log_flush and emit_tail together
- **Suggested revision**: Address the concern above.


### FINDING_15: risk-integration: docs/linting.md:150
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] docs/linting.md lists 10 test-step-7a cases but harness documents 16 Contributors may think rebase and crash paths are out of scope Sync docs/linting.md inventory with test-step-7a.md case list
- **Suggested revision**: Address the concern above.


### FINDING_19: correctness: skills/implement/scripts/step-7a.sh:58-63,376-378
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] should_skip_diagram_upsert omits several sanitizer REASON_TOKEN values. When sanitize rejects with br-in-participant-alias dollar-in-participant-alias or unclosed-frontmatter step-7a still upserts a misleading larch:diagrams placeholder comment. Match all REASON_TOKEN literals from sanitize-mermaid-fragment.sh or skip upsert on all STATUS=skipped from generator; extend tests.
- **Suggested revision**: Address the concern above.


### FINDING_2: correctness: skills/implement/scripts/step-7a.sh:376-378
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Sanitizer upsert suppression is incomplete relative to plan and sibling docs. Live /implement runs can publish larch:diagrams after sanitizer rejection on tokens not covered by the case list, contradicting Round 1 Decision 2. Same as finding 1: gate on STATUS=skipped from generate-code-flow-diagram.sh instead of substring heuristics.
- **Suggested revision**: Address the concern above.


### FINDING_22: code-quality: skills/implement/scripts/step-7a.sh:410,126-137
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] set -e after rebase is cleared by set +e inside run_larch_log_write. Post-rebase errexit does not protect flush or emit_tail as intended. Save/restore errexit around run_larch_log_write or avoid global set +e in the function.
- **Suggested revision**: Address the concern above.


### FINDING_26: correctness: skills/implement/scripts/step-7a.sh:58-62,376-399
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Sanitizer rejection skips larch:diagrams upsert but main SKILL always upserted placeholder comment STATUS=skipped with sanitizer SKIP_REASON leaves tracking issue without updated larch:diagrams comment that main would post with Code flow diagram not available Restore upsert on sanitizer path for byte-identical behavior or revise acceptance and document intentional skip-upsert
- **Suggested revision**: Address the concern above.


### FINDING_29: correctness: skills/implement/scripts/step-7a.sh:410
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] set -e enabled after successful rebase contradicts plan non-e bootstrap Unguarded post-rebase failure may abort with undocumented non-zero exit instead of degraded KV tail Remove set -e or keep set +e through final exit 0
- **Suggested revision**: Address the concern above.


### FINDING_30: **correctness** `skills/implement/scripts/step-7a.sh:410-422` — The script deliberately omits `-e` at the top (`set -uo pipefail`, line 4) so child failures are handled via explicit `rc` checks and `append-tool-failure.sh`, but line 410 turns errexit on for the rebase KV re-emit loop and never restores it before the tail. `run_log_flush` (line 421) immediately executes `set +e` (line 151), which disables errexit for the rest of the process; `emit_tail` (line 422) therefore runs with errexit off. Net effect: a failing `emit` in the `while read` loop (lines 411–414) can abort the script **before** pre-bump flush, while failures in the final KV tail are silently ignored—opposite halves of an inconsistent policy. **Suggested fix:** Drop the mid-script `set -e` (keep the planned no-`-e` orchestration model) and handle re-emit failures explicitly if needed; if errexit is truly required for that loop, wrap only that loop and run `set +e` (or restore the prior option state) before calling `run_log_flush` / `emit_tail`.
- **Reviewer**: dyn-shell-mode-flags-output.txt
- **Concern**: - **correctness** `skills/implement/scripts/step-7a.sh:410-422` — The script deliberately omits `-e` at the top (`set -uo pipefail`, line 4) so child failures are handled via explicit `rc` checks and `append-tool-failure.sh`, but line 410 turns errexit on for the rebase KV re-emit loop and never restores it before the tail. `run_log_flush` (line 421) immediately executes `set +e` (line 151), which disables errexit for the rest of the process; `emit_tail` (line 422) therefore runs with errexit off. Net effect: a failing `emit` in the `while read` loop (lines 411–414) can abort the script **before** pre-bump flush, while failures in the final KV tail are silently ignored—opposite halves of an inconsistent policy. **Suggested fix:** Drop the mid-script `set -e` (keep the planned no-`-e` orchestration model) and handle re-emit failures explicitly if needed; if errexit is truly required for that loop, wrap only that loop and run `set +e` (or restore the prior option state) before calling `run_log_flush` / `emit_tail`.
- **Suggested revision**: Address the concern above.


### FINDING_34: **architecture** `skills/implement/SKILL.md:123-134` — The canonical **Rebase Checkpoint Macro** still tells the orchestrator to “Run the foreground `rebase-checkpoint-probe.sh` invocation” and treats every registry row (including `7a.r`) as a direct probe Bash call, but Step 7a now runs a single `step-7a.sh` wrapper. Step 7a prose at `1434` correctly says to apply macro routing after `step-7a.sh` returns and that the helper preserves the probe exit code, yet the Macro section never states that for `7a.r` the **process exit code to branch on is `step-7a.sh`’s exit** (1/3 on conflict/failure), not a standalone probe fence. That split contract makes KV-only routing (`REBASE_OUTCOME` parsing without honoring non-zero Bash exit) more likely and undermines the deliberate propagation in `skills/implement/scripts/step-7a.sh:415-418`. **Suggested fix:** Add a `7a.r` call-site exception in `## Rebase Checkpoint Macro` (registry note + orchestrator step 1) stating that `7a.r` is reached via `step-7a.sh`, macro routing must use the wrapper’s combined stdout **and** its process exit code, and pre-bump flush only occurs inside the helper when `REBASE_OUTCOME=ok|skipped`.
- **Reviewer**: dyn-rebase-exit-propagation-output.txt
- **Concern**: - **architecture** `skills/implement/SKILL.md:123-134` — The canonical **Rebase Checkpoint Macro** still tells the orchestrator to “Run the foreground `rebase-checkpoint-probe.sh` invocation” and treats every registry row (including `7a.r`) as a direct probe Bash call, but Step 7a now runs a single `step-7a.sh` wrapper. Step 7a prose at `1434` correctly says to apply macro routing after `step-7a.sh` returns and that the helper preserves the probe exit code, yet the Macro section never states that for `7a.r` the **process exit code to branch on is `step-7a.sh`’s exit** (1/3 on conflict/failure), not a standalone probe fence. That split contract makes KV-only routing (`REBASE_OUTCOME` parsing without honoring non-zero Bash exit) more likely and undermines the deliberate propagation in `skills/implement/scripts/step-7a.sh:415-418`. **Suggested fix:** Add a `7a.r` call-site exception in `## Rebase Checkpoint Macro` (registry note + orchestrator step 1) stating that `7a.r` is reached via `step-7a.sh`, macro routing must use the wrapper’s combined stdout **and** its process exit code, and pre-bump flush only occurs inside the helper when `REBASE_OUTCOME=ok|skipped`.
- **Suggested revision**: Address the concern above.


### FINDING_4: code-quality: skills/implement/scripts/step-7a.sh:410
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Mid-script set -e breaks the file's explicit rc-handling style. A later unguarded command inside run_log_flush could abort the script before emit_tail without the intended degraded KV tail. Remove set -e and keep set +e or rc=$? around fallible calls like the rest of the script.
- **Suggested revision**: Address the concern above.


### FINDING_43: **correctness** `skills/implement/scripts/step-7a.sh:58-62` — `should_skip_diagram_upsert` only suppresses the `larch:diagrams` upsert for `pipe-in-node-label`, `sanitizer-*`, `*sanitiz*`, and `*reject*`. Production sanitizer rejection flows through `generate-code-flow-diagram.sh:99-102`, which always emits `STATUS=skipped` with `SKIP_REASON` taken from the first `REASON_TOKEN` in the sanitizer log (`scripts/sanitize-mermaid-fragment.sh:201-238`). Three of the four real tokens (`br-in-participant-alias`, `dollar-in-participant-alias`, `unclosed-frontmatter`) match none of those patterns, so Step 7a still composes `summary-diagrams.md` and calls `tracking-issue-summary.sh` for those rejections. That contradicts `step-7a.md:48` (“Sanitizer rejection suppresses the `larch:diagrams` upsert”) and leaves skip-upsert behavior dependent on which sanitizer rule fired. **Suggested fix:** Treat `STATUS=skipped` from `generate-code-flow-diagram.sh` as the sanitizer-rejection signal (that script has no other `skipped` exit today), or enumerate every `REASON_TOKEN` from `scripts/sanitize-mermaid-fragment.sh:201-238` explicitly; add harness cases for each token so regressions cannot hide behind the `pipe-in-node-label`-only stub.
- **Reviewer**: dyn-sanitizer-rejection-semantics-output.txt
- **Concern**: - **correctness** `skills/implement/scripts/step-7a.sh:58-62` — `should_skip_diagram_upsert` only suppresses the `larch:diagrams` upsert for `pipe-in-node-label`, `sanitizer-*`, `*sanitiz*`, and `*reject*`. Production sanitizer rejection flows through `generate-code-flow-diagram.sh:99-102`, which always emits `STATUS=skipped` with `SKIP_REASON` taken from the first `REASON_TOKEN` in the sanitizer log (`scripts/sanitize-mermaid-fragment.sh:201-238`). Three of the four real tokens (`br-in-participant-alias`, `dollar-in-participant-alias`, `unclosed-frontmatter`) match none of those patterns, so Step 7a still composes `summary-diagrams.md` and calls `tracking-issue-summary.sh` for those rejections. That contradicts `step-7a.md:48` (“Sanitizer rejection suppresses the `larch:diagrams` upsert”) and leaves skip-upsert behavior dependent on which sanitizer rule fired. **Suggested fix:** Treat `STATUS=skipped` from `generate-code-flow-diagram.sh` as the sanitizer-rejection signal (that script has no other `skipped` exit today), or enumerate every `REASON_TOKEN` from `scripts/sanitize-mermaid-fragment.sh:201-238` explicitly; add harness cases for each token so regressions cannot hide behind the `pipe-in-node-label`-only stub.
- **Suggested revision**: Address the concern above.


### FINDING_44: **correctness** `skills/implement/scripts/step-7a.sh:358-377` — Even for tokens that do match `should_skip_diagram_upsert`, suppressing the upsert is a behavior change relative to `main` `skills/implement/SKILL.md` (removed lines in the branch diff around the old Step 7a block): main always posted the `larch:diagrams` comment with the `"Code flow diagram not available."` placeholder on sanitizer rejection and only logged a warning when `STATUS=failed`. The branch now skips upsert for some sanitizer paths but not others (see finding above), so acceptance text claiming a preserved “sanitizer-rejection skip path” and “byte-identical” comment output is only partially true. **Suggested fix:** Decide explicitly whether skip-upsert is the intended product change; if yes, skip for all sanitizer `STATUS=skipped` outcomes and document the divergence from main in `step-7a.md` / `SKILL.md`; if no, remove `COMMENT_UPSERT_SKIP` and restore unconditional upsert to match main.
- **Reviewer**: dyn-sanitizer-rejection-semantics-output.txt
- **Concern**: - **correctness** `skills/implement/scripts/step-7a.sh:358-377` — Even for tokens that do match `should_skip_diagram_upsert`, suppressing the upsert is a behavior change relative to `main` `skills/implement/SKILL.md` (removed lines in the branch diff around the old Step 7a block): main always posted the `larch:diagrams` comment with the `"Code flow diagram not available."` placeholder on sanitizer rejection and only logged a warning when `STATUS=failed`. The branch now skips upsert for some sanitizer paths but not others (see finding above), so acceptance text claiming a preserved “sanitizer-rejection skip path” and “byte-identical” comment output is only partially true. **Suggested fix:** Decide explicitly whether skip-upsert is the intended product change; if yes, skip for all sanitizer `STATUS=skipped` outcomes and document the divergence from main in `step-7a.md` / `SKILL.md`; if no, remove `COMMENT_UPSERT_SKIP` and restore unconditional upsert to match main.
- **Suggested revision**: Address the concern above.


### FINDING_46: **correctness** `skills/implement/scripts/test-step-7a.sh:122-125,365-375` — The `diagram-rejected` case correctly models production (`STATUS=skipped`, `SKIP_REASON=pipe-in-node-label`) rather than the plan’s synthetic `STATUS=failed` / `sanitizer-rejected` pair, but it only exercises one of four sanitizer tokens and therefore would not catch the incomplete `should_skip_diagram_upsert` list. The harness also asserts no Warning for sanitizer rejection, which aligns with production (`generate-code-flow-diagram.sh` exits 0 on sanitizer skip) but differs from the plan’s “failed + warning” expectation. **Suggested fix:** Add one harness case per `REASON_TOKEN` (or a parameterized loop) asserting `tracking-issue-summary.sh` is absent from `calls.log` and `COMMENT_URL` is empty; keep `diagram-skipped-non-sanitizer` only if the generator contract gains a real non-sanitizer `STATUS=skipped` path.
- **Reviewer**: dyn-sanitizer-rejection-semantics-output.txt
- **Concern**: - **correctness** `skills/implement/scripts/test-step-7a.sh:122-125,365-375` — The `diagram-rejected` case correctly models production (`STATUS=skipped`, `SKIP_REASON=pipe-in-node-label`) rather than the plan’s synthetic `STATUS=failed` / `sanitizer-rejected` pair, but it only exercises one of four sanitizer tokens and therefore would not catch the incomplete `should_skip_diagram_upsert` list. The harness also asserts no Warning for sanitizer rejection, which aligns with production (`generate-code-flow-diagram.sh` exits 0 on sanitizer skip) but differs from the plan’s “failed + warning” expectation. **Suggested fix:** Add one harness case per `REASON_TOKEN` (or a parameterized loop) asserting `tracking-issue-summary.sh` is absent from `calls.log` and `COMMENT_URL` is empty; keep `diagram-skipped-non-sanitizer` only if the generator contract gains a real non-sanitizer `STATUS=skipped` path.
- **Suggested revision**: Address the concern above.


### FINDING_8: correctness: skills/implement/scripts/step-7a.sh:58-63
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] should_skip_diagram_upsert omits several sanitizer REASON_TOKEN values br-in-participant-alias rejection still upserts larch:diagrams with placeholder while plan/harness assume sanitizer rejection skips upsert Match all sanitize-mermaid REASON_TOKEN values or treat any skipped diagram with REASON_TOKEN as no-upsert; add harness case
- **Suggested revision**: Address the concern above.


### FINDING_9: correctness: skills/implement/scripts/step-7a.sh:383-398
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Sanitizer path skips upsert but main always upserted; conflicts with byte-identical acceptance pipe-in-node-label rejection leaves stale GitHub comment instead of updated placeholder Clarify acceptance or restore always-upsert on sanitizer rejection
- **Suggested revision**: Address the concern above.


