### FINDING_1: Step 3 fence does not fail closed on driver failure or stale result env
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-driver-output.txt, dyn-round-state-output.txt
- **Severity**: important
- **Concern**: The orchestrator captures `run-step3-review.sh` exit status but can continue by sourcing stale or incomplete `.step3-review-result.env`, including after HARD cursor advance failure, launcher errors, failed writes, or abort-before-write paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-driver-output.txt, dyn-round-state-output.txt: Address the concern above.

### FINDING_2: Documented stdout KV fallback is not implemented
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-driver-output.txt, dyn-round-state-output.txt, dyn-quiet-io-output.txt
- **Severity**: important
- **Concern**: `SKILL.md` promises stdout KV fallback, but `_plan_review_out` is not parsed when `.step3-review-result.env` is missing, symlink-refused, or unreadable. With quiet stream capture, this can leave branch-matrix variables unset and hide emitted diagnostics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-driver-output.txt, dyn-round-state-output.txt, dyn-quiet-io-output.txt: Address the concern above.

### FINDING_3: Step 3 driver duplicates result-env parsing instead of using shared helper
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `run-step3-review.sh` reimplements allowlisted result-env parsing instead of exercising `phase_driver_read_result_env`, increasing drift risk for this and future extracted phase drivers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_4: Collector stderr behavior changed without dedicated scope or test coverage
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-quiet-io-output.txt
- **Severity**: important
- **Concern**: `plan-review-loop.sh` collector stderr changed from live tee/forwarding to buffered replay, altering observability and ordering during long or failed collection without a dedicated contract, doc update, or behavioral harness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-quiet-io-output.txt: Address the concern above.

### FINDING_5: Redundant cap-env re-source creates dead cap branch
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `run-step3-review.sh` re-sources `.step3-review-cap.env` and checks `STEP3_REVIEW_CAP_REACHED` again after the outer cap guard, leaving confusing dead control flow.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_6: Unused `_allow` array remains in Step 3 driver
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `run-step3-review.sh` declares `_allow` but never reads it, which can mislead maintainers and may fail stricter future shell linting.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_7: Cap env persistence uses inconsistent non-atomic primitive
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `.step3-review-cap.env` is written with `cat >` while sibling result env state uses `phase_driver_write_result_env`, creating inconsistent state persistence in the same driver.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] Implement step2 duplicates `phase_driver_session_get`
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `run-step2-dispatch.sh` keeps a pre-existing `session_get` duplicate instead of using the new shared phase-driver primitive.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] Gate B docs still reference old Step 3 result env
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `approval-gates.md` references `.step3-plan-review-result.env` where the extracted Step 3 wrapper now uses `.step3-review-result.env`, risking stale guidance around inner versus normalized outer artifacts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_10: Cap-reached entry path omits skip breadcrumb
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: When the primary cap-reached guard fires, the panel is skipped without emitting the previous `cap reached; skipping` breadcrumb, reducing operator visibility on re-entry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_11: `ROUND_NUM` is no longer propagated to the Step 3 fence
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Main-agent vote paths can see empty `ROUND_NUM`, causing downstream paths such as `round-/findings-classification.tsv`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_12: Step 3 harness does not assert the full normalized result-env contract
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-harness-parity-output.txt
- **Severity**: important
- **Concern**: Tests only check a subset of normalized keys, so missing or renamed keys such as `STEP3_REVIEW_CAP_REACHED`, `TALLY_PLAN_REVIEW_STATUS`, or counts could pass CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, dyn-harness-parity-output.txt: Address the concern above.

### FINDING_13: Launcher argv validation coverage is incomplete
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The new argv rule is only tested for missing `--design-tmpdir`; missing required flags and unknown options could exit with the wrong status or message unnoticed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_14: `LOOP_STATUS=tally-error` rollback branch is untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-harness-parity-output.txt
- **Severity**: latent
- **Concern**: Rollback coverage exercises tally-status errors but not the branch where `LOOP_STATUS` itself is `tally-error`, leaving round-count rollback behavior unpinned.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, dyn-harness-parity-output.txt: Address the concern above.

### FINDING_15: Multi-round integration bypasses `run-step3-review.sh`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Full multi-round integration does not exercise the new wrapper, so wrapper regressions in cap, cursor, or persistence behavior rely only on narrower harnesses.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_16: `CLAUDE_PLUGIN_ROOT` precedence lacks unit coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-harness-parity-output.txt
- **Severity**: nit
- **Concern**: `phase_driver_resolve_plugin_root` documents env-var precedence over session env and tree walk, but the harness does not assert that branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-harness-parity-output.txt: Address the concern above.

### FINDING_17: Main-agent re-tally can leave outer normalized env stale
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Main-agent re-tally refreshes the inner `.step3-plan-review-result.env` but not the outer `.step3-review-result.env`, so later logic may still see `main-agent-vote-required` after adjudication.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_18: Final result-env write return value is unchecked
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `run-step3-review.sh` can exit successfully even if `phase_driver_write_result_env` fails, allowing the orchestrator to read stale normalized state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_19: Cap-reached path skips round forensics cleanup
- **Reviewer(s)**: dyn-round-state-output.txt
- **Severity**: important
- **Concern**: When cap is reached at entry, stale `plan-review/round-*` artifacts are not cleaned even though the old flow cleared them on every Step 3 entry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-round-state-output.txt: Address the concern above.

### FINDING_20: Operator-facing diagnostics use the contract stream after quiet init
- **Reviewer(s)**: dyn-quiet-io-output.txt
- **Severity**: latent
- **Concern**: Human warnings and breadcrumbs in `run-step3-review.sh` are emitted through `emit`/FD 3 after `larch_quiet_init`, mixing diagnostics with machine KVs and making them easy to capture or lose.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-quiet-io-output.txt: Address the concern above.

### FINDING_21: Inner-loop `WARN` lines can disappear from Step 3 chat surface
- **Reviewer(s)**: dyn-quiet-io-output.txt
- **Severity**: latent
- **Concern**: `WARN=` lines are republished with `emit_kv WARN`, but the new fence does not read `WARN` from the normalized env or `_plan_review_out`, so panel warnings may not be surfaced.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-quiet-io-output.txt: Address the concern above.

### FINDING_22: Inner result-env file-first parsing lacks behavioral harness coverage
- **Reviewer(s)**: dyn-harness-parity-output.txt
- **Severity**: important
- **Concern**: The moved parser for `.step3-plan-review-result.env` is not covered for real file, symlinked file, or stdout-precedence scenarios.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-parity-output.txt: Address the concern above.

### FINDING_23: `test-step3-review-cap.sh` snapshot stub is dead
- **Reviewer(s)**: dyn-harness-parity-output.txt
- **Severity**: nit
- **Concern**: The harness installs fixture `snapshot-plan-round.sh` files under tmp roots, but `run_driver` points `CLAUDE_PLUGIN_ROOT` at the real repo, so those fixtures are never invoked.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-parity-output.txt: Address the concern above.

### FINDING_24: [OUT_OF_SCOPE] Step2 dispatch argv coverage remains thin
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Existing step2 dispatch tests have similarly thin argv coverage; this was not introduced by the Step 3 extraction.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_25: [OUT_OF_SCOPE] Cap env read/write path has symlink security risk
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `.step3-review-cap.env` is written with `cat >` and later sourced without symlink refusal, which could truncate arbitrary targets or source attacker-controlled shell in a shared-writable tmpdir.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_26: [OUT_OF_SCOPE] Result-env parser does not reject newline-bearing values
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Allowlisted KV parsing can accept values containing newlines, letting a malicious env file create extra apparent `KEY=value` lines on later reads.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_27: [OUT_OF_SCOPE] Test hook can redirect Step 3 loop execution
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `RUN_STEP3_PLAN_REVIEW_LOOP_SH` can point execution at any executable path; this is pre-existing test-hook class risk if an untrusted parent controls environment.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_28: [OUT_OF_SCOPE] Dead cap re-check also hides the skip breadcrumb on normal entry
- **Reviewer(s)**: dyn-bash-driver-output.txt, dyn-round-state-output.txt
- **Severity**: latent
- **Concern**: Dynamic reviewers marked the inner cap re-check as unreachable in normal flow and separately noted that the visible skip breadcrumb only appears on that dead path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-driver-output.txt, dyn-round-state-output.txt: Address the concern above.

### FINDING_29: [OUT_OF_SCOPE] Collector stderr buffering noted as observability-only by one reviewer
- **Reviewer(s)**: dyn-bash-driver-output.txt
- **Severity**: latent
- **Concern**: The buffered collector stderr behavior may affect live diagnostic streaming even if it is unlikely to change loop status or tally state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-driver-output.txt: Address the concern above.

### FINDING_30: [OUT_OF_SCOPE] Unused `_allow` and duplicate parsing noted as no-runtime-effect
- **Reviewer(s)**: dyn-bash-driver-output.txt, dyn-quiet-io-output.txt
- **Severity**: nit
- **Concern**: Dynamic reviewers separately classified the unused `_allow` array and unused shared parser as harmless duplication rather than a runtime defect.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-driver-output.txt, dyn-quiet-io-output.txt: Address the concern above.

### FINDING_31: [OUT_OF_SCOPE] Cap cleanup contract and tests are not aligned
- **Reviewer(s)**: dyn-round-state-output.txt
- **Severity**: latent
- **Concern**: The Step 3 contract says round forensics cleanup is unconditional, but cap-reached implementation and tests do not enforce that behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-round-state-output.txt: Address the concern above.

### FINDING_32: [OUT_OF_SCOPE] Normalized env omits inner-loop keys
- **Reviewer(s)**: dyn-quiet-io-output.txt
- **Severity**: nit
- **Concern**: The outer `.step3-review-result.env` omits some inner-loop keys such as `REASON` and `REVISE_STATUS`; the reviewer judged this not currently amplified because `SKILL.md` does not reference them after Step 3.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-quiet-io-output.txt: Address the concern above.

### FINDING_33: [OUT_OF_SCOPE] Larch logs commit is unrelated to runtime behavior
- **Reviewer(s)**: dyn-quiet-io-output.txt
- **Severity**: nit
- **Concern**: Commit `1f5b1c922` was identified as unrelated to quiet-io runtime behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-quiet-io-output.txt: Address the concern above.

### FINDING_34: [OUT_OF_SCOPE] Makefile and shard wiring appear correct
- **Reviewer(s)**: dyn-harness-parity-output.txt
- **Severity**: nit
- **Concern**: `test-run-step3-review` and `test-lib-phase-driver` are registered and included in the relevant harness shard; no wiring defect was identified.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-parity-output.txt: Address the concern above.

### FINDING_35: [OUT_OF_SCOPE] Step 3 harnesses overlap heavily
- **Reviewer(s)**: dyn-harness-parity-output.txt
- **Severity**: nit
- **Concern**: `test-run-step3-review.sh` and `test-step3-review-cap.sh` cover overlapping cap, failure, rollback, and normalization behavior; this is redundant but not inherently wrong.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-parity-output.txt: Address the concern above.

### FINDING_36: [OUT_OF_SCOPE] New harness documentation is sparse
- **Reviewer(s)**: dyn-harness-parity-output.txt
- **Severity**: nit
- **Concern**: `test-run-step3-review.md` and `test-lib-phase-driver.md` are minimal compared with richer sibling harness docs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-parity-output.txt: Address the concern above.

### FINDING_37: [OUT_OF_SCOPE] Additional Step 3 plan edge cases lack behavioral tests
- **Reviewer(s)**: dyn-harness-parity-output.txt
- **Severity**: latent
- **Concern**: Non-numeric round counts, HARD cursor exit 1, and missing required argv flags remain without direct behavioral tests in the reviewer’s out-of-scope list.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-parity-output.txt: Address the concern above.

### FINDING_38: [OUT_OF_SCOPE] Branch commit list surfaced as context only
- **Reviewer(s)**: dyn-harness-parity-output.txt
- **Severity**: nit
- **Concern**: The reviewer listed branch commits `b9806b39d`, `1f5b1c922`, and `a4fb82a02` as contextual observations rather than a behavioral finding.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-parity-output.txt: Address the concern above.
