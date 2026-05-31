### FINDING_1: Step 3 fence does not fail closed on driver failure or stale result env
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-driver-output.txt, dyn-round-state-output.txt
- **Severity**: important
- **Concern**: The orchestrator captures `run-step3-review.sh` exit status but can continue by sourcing stale or incomplete `.step3-review-result.env`, including after HARD cursor advance failure, launcher errors, failed writes, or abort-before-write paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-driver-output.txt, dyn-round-state-output.txt: Address the concern above.


### FINDING_10: Cap-reached entry path omits skip breadcrumb
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: When the primary cap-reached guard fires, the panel is skipped without emitting the previous `cap reached; skipping` breadcrumb, reducing operator visibility on re-entry.
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


### FINDING_17: Main-agent re-tally can leave outer normalized env stale
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Main-agent re-tally refreshes the inner `.step3-plan-review-result.env` but not the outer `.step3-review-result.env`, so later logic may still see `main-agent-vote-required` after adjudication.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_2: Documented stdout KV fallback is not implemented
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-driver-output.txt, dyn-round-state-output.txt, dyn-quiet-io-output.txt
- **Severity**: important
- **Concern**: `SKILL.md` promises stdout KV fallback, but `_plan_review_out` is not parsed when `.step3-review-result.env` is missing, symlink-refused, or unreadable. With quiet stream capture, this can leave branch-matrix variables unset and hide emitted diagnostics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-driver-output.txt, dyn-round-state-output.txt, dyn-quiet-io-output.txt: Address the concern above.


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


### FINDING_4: Collector stderr behavior changed without dedicated scope or test coverage
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-quiet-io-output.txt
- **Severity**: important
- **Concern**: `plan-review-loop.sh` collector stderr changed from live tee/forwarding to buffered replay, altering observability and ordering during long or failed collection without a dedicated contract, doc update, or behavioral harness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-quiet-io-output.txt: Address the concern above.


