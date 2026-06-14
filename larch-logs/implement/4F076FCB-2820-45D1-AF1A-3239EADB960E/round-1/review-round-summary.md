# Review Round 1

- Mode: `diff`
- 9 accepted, 22 rejected (2 neutral)

## Accepted Findings

### FINDING_1: correctness: skills/design/references/brainstorm.md:103-110
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Brainstorm dirty-tree operator recovery prose and sidecar consult were removed while collect still sets RECOVERY_REQUIRED=true. External reviewer dirties the repo during brainstorm; collect writes dirty-tree-detected.env and WARN but /design continues to synthesis with no AskUserQuestion recovery gate, contradicting plan non-goals and main behavior. Restore post-collect recovery in brainstorm.md (sidecar consult plus .dirty-tree-prompted-brainstorm-collection prompt) or mandate an equivalent orchestrator branch on wrapper output before synthesis; optionally merge sidecar consult into --mode collect.
- **Suggested revision**: Address the concern above.


### FINDING_10: risk-integration: skills/design/references/brainstorm.md:103-110
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Brainstorm dirty-tree operator recovery prose was removed when collect moved into the wrapper; only WARN= and dirty-tree-detected.env remain. External reviewer pollutes the working tree during brainstorm; collect writes RECOVERY_REQUIRED=true but nothing prompts the operator, so synthesis and later plan steps proceed on a dirty tree. Restore post-collect recovery instructions in brainstorm.md: read dirty-tree-detected.env, prompt once via .dirty-tree-prompted-brainstorm-collection, block until clean or cancel.
- **Suggested revision**: Address the concern above.


### FINDING_14: risk-integration: skills/design/scripts/design-step1d5.sh:160-168
- **Reviewer**: codex-specialist-edge-cases-output.txt
- **Concern**: [important] Brainstorm dirty-tree recovery now records RECOVERY_REQUIRED=true without an operator recovery path. A dirty or unknown brainstorm collection continues into later design steps, and the stale dirty-tree-detected.env can affect design-step2b-postplan.sh:194-203 even though the stage is brainstorm-collection. Restore a brainstorm collection recovery branch that prompts, verifies clean, and clears or rewrites the env, or make the wrapper fully handle/cancel recovery before returning.
- **Suggested revision**: Address the concern above.


### FINDING_15: risk-integration: python/agents.py:3543-3549
- **Reviewer**: codex-specialist-edge-cases-output.txt
- **Concern**: [important] Codex brainstorm auth setup failures do not write the stderr sink that design-step1d5.sh ingests. When _prepare_codex_home fails, collection can report the failed slot but no codex-brainstorm-launch.failure.log exists, so no centralized External Reviewer Issues row is appended. Call _review_write_failure_sink for codex-brainstorm auth_rc failures with --stderr-sink, or append non-OK collector records when no sink exists.
- **Suggested revision**: Address the concern above.


### FINDING_2: correctness: python/agents.py:3543-3549
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Codex auth preflight failures on brainstorm launches do not call _review_write_failure_sink. Codex scope brainstorm fails _prepare_codex_home with --stderr-sink set; sink stays empty and collect never logs External Reviewer Issues for that launch. Call _review_write_failure_sink on auth failure when _review_brainstorm_failure_uses_sink is true; add codex-brainstorm pytest parity with cursor.
- **Suggested revision**: Address the concern above.


### FINDING_22: risk-integration: skills/design/references/brainstorm.md:103-110
- **Reviewer**: codex-specialist-testing-output.txt
- **Concern**: [important] Brainstorm dirty-tree recovery prompt was removed. A dirty or unknown checkpoint after external brainstorm collection writes RECOVERY_REQUIRED=true but continues into later design steps without operator recovery or clearing the sidecar. Restore the prompt-side recovery branch after --mode collect; prompt once, require a clean checkpoint before continuing, clear RECOVERY_REQUIRED, or cancel.
- **Suggested revision**: Address the concern above.


### FINDING_23: risk-integration: python/agents.py:3543-3549
- **Reviewer**: codex-specialist-testing-output.txt
- **Concern**: [important] Codex brainstorm auth setup failures do not write the configured stderr sink. A Codex auth/preflight failure leaves no codex-brainstorm launch log for design-step1d5.sh to ingest, so the run log can miss the External Reviewer Issues row. Write the sink in the auth_rc branch for brainstorm timing kinds and add a Codex brainstorm preflight regression test.
- **Suggested revision**: Address the concern above.


### FINDING_24: **correctness** `skills/design/references/brainstorm.md:103-110` — The branch deletes the post-collection dirty-tree operator contract that existed on `main` (sidecar consult, `AskUserQuestion`, and `.dirty-tree-prompted-brainstorm-collection` sentinel) and replaces it with wrapper-only side effects. `design-step1d5.sh` now writes `dirty-tree-detected.env` with `RECOVERY_REQUIRED=true` and prints `WARN=`, but neither `brainstorm.md` nor `SKILL.md` tells the orchestrator to stop for recovery before synthesis or Step 1d.7. That conflicts with the plan non-goal that operator recovery stays in `brainstorm.md`, and `/design` can continue with a dirty worktree after externals return. **Suggested fix:** Restore prompt-side recovery in `skills/design/references/brainstorm.md` immediately after `--mode collect`: consult `${OUTPUT}.dirty-tree` sidecars for supplied paths, branch on `dirty-tree-detected.env` / `RECOVERY_REQUIRED=true`, fire the once-per-boundary `AskUserQuestion` gated by `$DESIGN_TMPDIR/.dirty-tree-prompted-brainstorm-collection`, and do not proceed to synthesis until recovery clears or the operator cancels.
- **Reviewer**: dyn-brainstorm-flow-output.txt
- **Concern**: - **correctness** `skills/design/references/brainstorm.md:103-110` — The branch deletes the post-collection dirty-tree operator contract that existed on `main` (sidecar consult, `AskUserQuestion`, and `.dirty-tree-prompted-brainstorm-collection` sentinel) and replaces it with wrapper-only side effects. `design-step1d5.sh` now writes `dirty-tree-detected.env` with `RECOVERY_REQUIRED=true` and prints `WARN=`, but neither `brainstorm.md` nor `SKILL.md` tells the orchestrator to stop for recovery before synthesis or Step 1d.7. That conflicts with the plan non-goal that operator recovery stays in `brainstorm.md`, and `/design` can continue with a dirty worktree after externals return. **Suggested fix:** Restore prompt-side recovery in `skills/design/references/brainstorm.md` immediately after `--mode collect`: consult `${OUTPUT}.dirty-tree` sidecars for supplied paths, branch on `dirty-tree-detected.env` / `RECOVERY_REQUIRED=true`, fire the once-per-boundary `AskUserQuestion` gated by `$DESIGN_TMPDIR/.dirty-tree-prompted-brainstorm-collection`, and do not proceed to synthesis until recovery clears or the operator cancels.
- **Suggested revision**: Address the concern above.


### FINDING_7: correctness: skills/design/references/brainstorm.md:103-110
- **Reviewer**: codex-specialist-correctness-output.txt
- **Concern**: [important] Brainstorm dirty-tree recovery prompt was removed while the wrapper now only records RECOVERY_REQUIRED evidence. If a brainstorm external leaves the repo dirty, design-step1d5.sh writes dirty-tree-detected.env and WARN, but /design can proceed to synthesis and Step 1d.7 without recovery. Restore a post-collect recovery branch in brainstorm.md with a once-only prompt and clean re-check before continuing.
- **Suggested revision**: Address the concern above.


