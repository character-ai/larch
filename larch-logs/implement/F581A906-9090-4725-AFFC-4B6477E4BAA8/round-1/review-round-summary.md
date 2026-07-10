# Review Round 1

- Mode: `diff`
- 10 accepted, 1 rejected (1 neutral)

## Accepted Findings

### FINDING_1: Canonical run identity is inconsistent after PR-only run-ID resolution
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-bgjob-wire
- **Severity**: major
- **Concern**: When `FAILED_RUN_ID` is absent, the wrapper derives identity from `pr-<N>`, while the child resolves and persists a numeric run ID. Step identity, merge-result validation, rounds parsing, and subsequent tier re-entry can therefore disagree even after a successful child run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Recompute step/merge paths after run-id resolution or resolve run id in the wrapper first; persist and validate one canonical RUN_ID everywhere.
  - From cursor-specialist-testing: Align RUN_ID authority between wrapper and child; add integration test for missing-run-id resolution.
  - From dyn-dyn-bgjob-wire: Pick one canonical run-identity token for the whole wire (either always `pr-<N>` until ship state is updated, or always the resolved numeric id) and use it consistently in step hashing, `--run-id`/`--pr` child argv, `fixer-rounds.tsv`, merge-result env, and wrapper validation; after first resolution, persist the resolved id into ship state (or re-read it from `fixer-status.env`) before the next tier.
  - From dyn-dyn-bgjob-wire: Recompute `step` and `result_env` after run-id resolution (or resolve run id before computing step), and write the same `RUN_ID` value the wrapper will validate on re-entry.


### FINDING_2: Recoverable evidence failures are not persisted as typed operator-bail results
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, dyn-dyn-bgjob-wire
- **Severity**: major
- **Concern**: Evidence collection and related operational failures exit as closed failures with nonzero status and no verified merge-result envelope. The wrapper consequently cannot route them as typed operator-bail outcomes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Map evidence-class failures to operator-bail via _persist; exit 0 with verified merge env; reserve nonzero for pre-launch closed failures.
  - From codex-specialist-correctness: Translate recoverable evidence failures into a persisted and verified operator-bail result; use closed failure only when safe persistence itself fails.
  - From cursor-specialist-edge-cases: Map recoverable failures to operator-bail via _persist and exit 0; reserve non-zero exits for untrusted merge writes only.
  - From dyn-dyn-bgjob-wire: Route expected operational failures through `_persist(..., LaneResult("operator-bail", ...))` (or `retry-next-tool` where appropriate) and reserve non-zero exits for true closed failures where no safe typed envelope can be written.


### FINDING_3: FINAL_HEAD is not revalidated before result persistence
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: major
- **Concern**: The lane can persist a stale `FINAL_HEAD` if the repository changes after the earlier validation but before persistence, allowing stale status and merge payloads to be accepted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Read and validate HEAD immediately before persistence, bind the fresh value into the result, and fail closed or emit a typed bail on drift.


### FINDING_4: Digest/distillation retry bound is missing
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: minor
- **Concern**: Evidence collection skips the plan-mandated bounded digest/distillation retry path and falls directly to simplified output or raw-log fallback.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Use ci distill-log (or equivalent) with explicit retry cap before raw-log fallback.
  - From cursor-specialist-edge-cases: Add a fixed retry loop around digest creation/validation before raw-log fallback.
  - From cursor-specialist-testing: Implement explicit bounded digest retries with tests for retry exhaustion and fallback.


### FINDING_6: Rounds are committed before the complete result envelope is verified
- **Reviewer(s)**: codex-specialist-edge-cases, dyn-dyn-bgjob-wire
- **Severity**: major
- **Concern**: `_persist` can commit a rounds row and status artifact before merge-result persistence and verification complete. A later write failure leaves partially advanced durable state and can cause recovery to skip a tier without a safe typed result.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Commit the rounds row only after all result artifacts verify, or roll back earlier artifacts when a later persistence step fails.
  - From dyn-dyn-bgjob-wire: Write the merge-result env first (or use a single atomic handoff transaction: temp dir + `rename`, or write-all-then-verify with cleanup on any mismatch).


### FINDING_7: Missing bgjob is not treated as a fresh-start condition
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: major
- **Concern**: A `DEAD` bgjob with `BGJOB_DIAG=missing-registry` and exit code 0 is treated as completed non-success, preventing the first fixer attempt from starting.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Branch explicitly on BGJOB_STATUS and start only for the missing-registry DEAD result.


### FINDING_8: Wrapper contract violations abort instead of producing a typed result
- **Reviewer(s)**: dyn-dyn-bgjob-wire
- **Severity**: major
- **Concern**: Terminal merge/status validation can exit with status 2 without emitting the bounded `RESULT=operator-bail` envelope, preventing downstream orchestration from distinguishing protocol rejection from an unhandled shell failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-bgjob-wire: Wrap the validator (`|| fail merge-status-disagreement`) or have it print `RESULT=operator-bail`/`REASON=...` and `exit 0` on all contract violations.


### FINDING_9: Behavioral coverage for the fixer lane is substantially incomplete
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing
- **Severity**: major
- **Concern**: Tests cover mostly registration, help text, or static shell checks. Identity validation, PR-only resolution, evidence handling, typed outcomes, persistence failures, merge/status disagreement, stale data, and re-entry behavior can regress without automated coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Add offline tests for PR-only resolution, multi-tier rounds, typed bail persistence, and merge/status disagreement.
  - From cursor-specialist-edge-cases: Implement the plan’s offline unit and shell harness cases for identity binding and typed routing.
  - From cursor-specialist-testing: Add injected-runner pytest coverage for every plan-listed child scenario and result token.
  - From codex-specialist-testing: Add offline injected-runner and launcher tests that invoke ci_fixer_lane.main() for typed outcomes and unsafe, stale, write-failure, and status/merge-consistency paths.


### FINDING_10: Step 8 shell harness does not exercise the bgjob routing matrix
- **Reviewer(s)**: cursor-specialist-testing, codex-specialist-testing
- **Severity**: major
- **Concern**: The harness lacks isolated fake CLI/bgjob cases for start, rejoin, WAIT, DONE, missing results, stale or symlinked data, identity mismatch, and merge-result-based routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Implement plan-specified stubbed cli.py/bgjob cases and assert routing from merge-result env only.
  - From codex-specialist-testing: Build isolated fake CLI and bgjob fixtures that exercise start, rejoin, WAIT, DONE, result forwarding, identity validation, stale and symlink rejection, and merge-result-based routing.


### FINDING_13: Monitor run-ID resolution and pending-state behavior lack focused tests
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: Tests cover only ready versus error evidence preparation, not `resolve_failed_run_id_once` or in-progress polling and re-resolution behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add focused tests with injected runner/sleep fakes for re-resolution and in-progress paths.
