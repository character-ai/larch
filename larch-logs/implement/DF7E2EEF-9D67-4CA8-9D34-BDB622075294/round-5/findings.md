### FINDING_1: Documentation allowlist omits `oos-accepted-design.md`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The documented artifact allowlist and plan basename documentation omit or drift from `lib-design-round-artifacts.sh`, where `oos-accepted-design.md` is allowed. Maintainers could update only one side and break publish/snapshot parity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_2: Drift harness misses `oos-accepted-design.md`
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `scripts/test-lib-design-round-artifacts.sh` does not assert `oos-accepted-design.md`, so removing it from the library can pass the drift test while breaking multi-round OOS forensics and publish parity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_3: Duplicated terminal convergence logic
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Snapshot-failure and success paths duplicate convergence streak and cap-hit logic, creating risk that future edits change one branch but not the other.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: Monolithic review loop script
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `plan-review-loop.sh` remains a large Bash script with many inline Python blocks, increasing review difficulty and regression risk when changing one concern such as OOS dedup.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: Round driver relies on mutable global state
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: The round driver still mutates globals read by the outer loop, so stale state from a previous round could affect convergence or revise handling if a reset is missed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_6: Loose accepted-finding grep pattern
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `ACCEPTED_COUNT` uses a looser `^### FINDING_` pattern than other tally paths, so malformed finding headings could skew convergence or cap-hit behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_7: Parser writes ephemeral Python per call
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `_parse_collect_records` writes a temporary Python script under `DESIGN_TMPDIR` on every call, adding tmpdir churn and making parser linting/unit testing harder.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_8: Symlinked plan-review cleanup lacks required warning
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Step 3 cleanup is skipped silently when `plan-review` is a symlink, contrary to the plan-required refuse plus WARN behavior, leaving stale round artifacts across entries.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_9: Missing cross-entry Step 3 integration coverage
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Integration coverage does not simulate two Step 3 entries with round reset and `review-round-count.txt` persistence, so Gate C rerun regressions can pass current harnesses.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] Unreachable terminal exit
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `_terminal_exit` after the main loop appears unreachable because all branches exit before it; this is dead code rather than a user-visible failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_11: Missing convergence and degraded-reset tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Harnesses lack explicit convergence-streak and degraded-streak-reset cases, so regressions in `convergence_streak`, `DEGRADED_PANEL` reset behavior, `REASON=streak`, completed round counts, and round artifact creation could ship.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_12: Revise snapshot copy can dereference symlinks
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `_snapshot_round_dir` checks session-root sources for symlinks but not `revise/` sources, allowing a same-UID writer to replace a revise output with a symlink that `cp` dereferences into published artifacts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_13: Auto-apply trust boundary is undocumented
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Multi-round auto-apply repeatedly feeds accepted finding prose into plan revision without per-round operator approval, creating a trust-boundary risk for malicious or security-tagged findings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_14: Result env writer does not reject symlink destination
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `write_step3_result_env` does not reject a symlinked `.step3-plan-review-result.env` destination before atomic `mv`, which could redirect the write to another same-UID path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_15: Snapshot deletes in-round classification TSV
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `_snapshot_round_dir` deletes non-revise children before copying allowlisted session-root files, but `findings-classification.tsv` is produced inside `plan-review/round-N/`, so multi-round terminal snapshots lose it before publish.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_16: Post-apply failures report revise status as ok
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `revise_status` is forced to `ok` before post-apply work, so validator or emit failures can produce `round-summary.env` with `REVISE_STATUS=ok` despite terminal failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_17: Emit failure leaves mutated plan committed
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `EMIT_PLAN` runs after in-loop mutation of `plan.txt`; if emit fails, the loop exits with a revised plan whose diff-lines trailer may be stale, affecting later Gate B manual handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_18: Snapshot failure aborts despite successful revise
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: A non-terminal snapshot failure exits as `panel-failed` even after successful review and revise, aborting the loop instead of continuing degraded or surfacing a dedicated status.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_19: OOS dedup can suppress distinct accepted items
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Cumulative OOS dedup uses bidirectional substring matching on description text, so distinct accepted OOS items sharing a phrase can collapse into one and be omitted from Step 5b.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_20: Degraded zero-findings reuses complete loop status
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Degraded zero-findings uses `LOOP_STATUS=complete` with `REASON=zero-findings-degraded-panel`, so downstream logic that keys only on `LOOP_STATUS` enters normal complete handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_21: [OUT_OF_SCOPE] In-loop dedup weaker than Gate B dedup
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: In-loop regex dedup is weaker than Gate B LLM dedup, so converged or cap-hit paths may keep semantic duplicates that Gate B would remove.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_22: Missing `_dedup_failed` reset coverage
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Tests do not verify that `_dedup_failed` resets per round; a dedup failure in one round could incorrectly degrade later rounds without CI catching it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_23: Missing Step 3 Gate B passive-summary integration test
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The SKILL.md Step 3 and Gate B passive-summary wiring is prose-only and lacks a branch-matrix or parser stub test, so operators depend on unverified KV mode handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_24: Integration path uses cap-hit instead of planned converge path
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: The integration test uses a round-cap-2 cap-hit path rather than the plan-specified three-round convergence path, leaving weaker end-to-end coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
