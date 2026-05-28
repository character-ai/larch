### FINDING_1: Documentation allowlist omits `oos-accepted-design.md`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The documented artifact allowlist and plan basename documentation omit or drift from `lib-design-round-artifacts.sh`, where `oos-accepted-design.md` is allowed. Maintainers could update only one side and break publish/snapshot parity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


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


### FINDING_15: Snapshot deletes in-round classification TSV
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `_snapshot_round_dir` deletes non-revise children before copying allowlisted session-root files, but `findings-classification.tsv` is produced inside `plan-review/round-N/`, so multi-round terminal snapshots lose it before publish.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_17: Emit failure leaves mutated plan committed
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `EMIT_PLAN` runs after in-loop mutation of `plan.txt`; if emit fails, the loop exits with a revised plan whose diff-lines trailer may be stale, affecting later Gate B manual handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_19: OOS dedup can suppress distinct accepted items
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Cumulative OOS dedup uses bidirectional substring matching on description text, so distinct accepted OOS items sharing a phrase can collapse into one and be omitted from Step 5b.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_2: Drift harness misses `oos-accepted-design.md`
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `scripts/test-lib-design-round-artifacts.sh` does not assert `oos-accepted-design.md`, so removing it from the library can pass the drift test while breaking multi-round OOS forensics and publish parity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_20: Degraded zero-findings reuses complete loop status
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Degraded zero-findings uses `LOOP_STATUS=complete` with `REASON=zero-findings-degraded-panel`, so downstream logic that keys only on `LOOP_STATUS` enters normal complete handling.
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

### FINDING_6: Loose accepted-finding grep pattern
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `ACCEPTED_COUNT` uses a looser `^### FINDING_` pattern than other tally paths, so malformed finding headings could skew convergence or cap-hit behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt: Address the concern above.


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


