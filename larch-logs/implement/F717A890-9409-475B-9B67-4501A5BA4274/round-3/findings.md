### FINDING_1: `_resume_plan` is too dense and mixes routing stages
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `_resume_plan` is a large mixed-responsibility function covering validation, GitHub routing, gh-skipped routing, and precedence decisions, making future routing changes regression-prone.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_2: Merge loop pre-stalls at iteration cap before observing CI/GitHub state
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-resume-state-output.txt, dyn-github-authority-output.txt, dyn-cap-loop-output.txt
- **Severity**: important
- **Concern**: The merge loop checks `iteration >= cap` before calling `ci_monitor.monitor()`, so an open-PR resume at the cap can stall without observing pass/already-merged outcomes that should still succeed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-resume-state-output.txt, dyn-github-authority-output.txt, dyn-cap-loop-output.txt: Address the concern above.

### FINDING_3: Fresh resume paths preserve stale counters while CI locals reset to zero
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-resume-state-output.txt, dyn-github-authority-output.txt, dyn-state-persistence-output.txt
- **Severity**: important
- **Concern**: Fresh fallback paths can carry persisted nonzero counters into state writes even though the CI loop seeds local counters to zero, causing inconsistent state and inflated budgets on later resumes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-resume-state-output.txt, dyn-github-authority-output.txt, dyn-state-persistence-output.txt: Address the concern above.

### FINDING_4: Iteration-cap stall handling is duplicated
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The CI loop has repeated iteration-cap stall blocks, increasing the chance that future cap-order fixes update only one path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: Boolean state parsing is duplicated
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `_state_bool_text` duplicates boolean parsing already present in `run_logs`, risking divergent handling of persisted flags over time.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_6: Open-PR resume OOS handling is inconsistent and may either rerun or skip gates incorrectly
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Reviewers disagree on the intended open-PR OOS policy, but the shared risk is that resume behavior is ambiguous: `OOS_PENDING=true` can re-enter OOS helpers despite skip-OOS expectations, while `OOS_PENDING=false` can skip remaining OOS/security artifacts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_7: `_resume_plan` raises on invalid REPO instead of returning a structured safe route
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, dyn-resume-state-output.txt
- **Severity**: latent
- **Concern**: Invalid or mismatched persisted `REPO` can raise `ShipError` and surface as `STALLED`, unlike other corrupt-state paths that degrade through structured resume outcomes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, dyn-resume-state-output.txt: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] Plan acceptance and regression test matrix is incomplete
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-resume-state-output.txt, dyn-github-authority-output.txt, dyn-state-persistence-output.txt, dyn-cap-loop-output.txt
- **Severity**: important
- **Concern**: Many plan-required cases lack dedicated tests, including cap-at-49/50 behavior, pass/already-merged at cap, stale GitHub/local state overrides, wrong PR head, blocked rebase re-entry, protected branch refusal, detached HEAD refusal, terminal counter round-trips, OOS-artifact resume behavior, and manifest non-done statuses.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-resume-state-output.txt, dyn-github-authority-output.txt, dyn-state-persistence-output.txt, dyn-cap-loop-output.txt: Address the concern above.

### FINDING_9: Normal-repo done resume is gated on manifest status despite GitHub MERGED + PHASE=done
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-resume-state-output.txt, dyn-github-authority-output.txt
- **Severity**: important
- **Concern**: For normal repos, `MERGED` with matching head and `PHASE=done` can rerun postmerge unless the manifest also says done, violating idempotent done-routing expectations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-resume-state-output.txt, dyn-github-authority-output.txt: Address the concern above.

### FINDING_10: Blocked rebase continuation can be preempted by REPO validation
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `RESUME_PHASE=ship-pr-rrr-phase14` with a repo mismatch can route to `STALLED` instead of the unsupported-continuation / user-input handback expected for blocked rebase continuation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_11: Terminal monitor handbacks may not persist consumed fix/rebase counters
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-cap-loop-output.txt
- **Severity**: important
- **Concern**: Terminal non-OK monitor exits can omit increments for consumed fixing/rebase work, allowing later invocations to under-count session-wide budgets.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-cap-loop-output.txt: Address the concern above.

### FINDING_12: Terminal state writes collapse non-OK phases to generic stalled
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `_write_terminal_state` loses specific stall-step granularity by collapsing non-OK phases to `stalled`, which may confuse resume routing or diagnostics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] State-file containment check may not reject symlink escapes
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: A symlink under the tmpdir could point outside the intended containment boundary unless real paths are resolved and validated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] Counter parsing accepts unbounded large values
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Corrupt huge counter values can be accepted as valid nonnegative session counters without sane upper bounds.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_15: [OUT_OF_SCOPE] Existing fresh-fallback test conflicts with the fresh-counter contract
- **Reviewer(s)**: dyn-resume-state-output.txt
- **Severity**: latent
- **Concern**: A test intentionally preserving counters on gh-failure fresh fallback conflicts with the plan line that fresh paths ignore stale counters and seed monitor counters at zero.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-resume-state-output.txt: Address the concern above.

### FINDING_16: `_materialize_manifest_oos` can clobber persisted counters
- **Reviewer(s)**: dyn-state-persistence-output.txt
- **Severity**: latent
- **Concern**: `_materialize_manifest_oos()` writes ship state without threading counter kwargs, so an OOS materialization write can reset counters to zero mid-run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-persistence-output.txt: Address the concern above.

### FINDING_17: `_write_ship_state` drops `CONFLICT_FILES` on routine rewrites
- **Reviewer(s)**: dyn-state-persistence-output.txt
- **Severity**: latent
- **Concern**: Routine full-file ship-state rewrites preserve some handoff fields but not `CONFLICT_FILES`, so conflict metadata can be lost after a pre-push handoff marker is bypassed or cleared.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-persistence-output.txt: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] Merge/postbump failure paths may return without terminal ship-state stall writes
- **Reviewer(s)**: dyn-state-persistence-output.txt
- **Severity**: latent
- **Concern**: Some merge/postbump failure branches still return without writing a terminal `ship-pr-state.sh` stall state, leaving only partial/finalize state in some paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-persistence-output.txt: Address the concern above.

### FINDING_19: Merge retry outcomes consume iteration budget unlike bash
- **Reviewer(s)**: dyn-cap-loop-output.txt
- **Severity**: important
- **Concern**: `ci_not_ready` and `main_advanced` merge results increment the Python loop iteration and can hit the cap, while bash retries those paths without consuming `ITERATION`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-cap-loop-output.txt: Address the concern above.

### FINDING_20: [OUT_OF_SCOPE] Manifest-gated done routing may reflect plan ambiguity
- **Reviewer(s)**: dyn-cap-loop-output.txt
- **Severity**: latent
- **Concern**: Existing tests encode manifest-gated done routing, but the plan wording appears stricter for gh-skipped versus GitHub-authoritative paths and should be tracked separately.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-cap-loop-output.txt: Address the concern above.

### FINDING_21: Manifest status can trust state `RUN_ID` during resume routing
- **Reviewer(s)**: dyn-statefile-hardening-output.txt
- **Severity**: important
- **Concern**: Resume routing can treat manifest status as authoritative through `effective_run_id()`, which prefers untrusted state `RUN_ID`; a tampered state file could point at another manifest and skip postmerge.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-statefile-hardening-output.txt: Address the concern above.

### FINDING_22: State-hydrated durable flags can force gh-skipped routing
- **Reviewer(s)**: dyn-statefile-hardening-output.txt
- **Severity**: important
- **Concern**: Durable flags read from state can disable GitHub ground-truth checks and route through gh-skipped local-state classification without caller/context agreement.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-statefile-hardening-output.txt: Address the concern above.

### FINDING_23: Resumed string fields are re-persisted without value-level validation
- **Reviewer(s)**: dyn-statefile-hardening-output.txt
- **Severity**: important
- **Concern**: `BRANCH_NAME`, `PR_URL`, and `MERGE_RESULT` can be hydrated and rewritten from state with only newline rejection, increasing risk when bash later consumes the same state keys.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-statefile-hardening-output.txt: Address the concern above.

### FINDING_24: [OUT_OF_SCOPE] `effective_run_id()` state preference itself predates this branch
- **Reviewer(s)**: dyn-statefile-hardening-output.txt
- **Severity**: nit
- **Concern**: The helper’s preference for state `RUN_ID` is pre-existing; the new concern is its use in resume routing rather than the helper alone.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-statefile-hardening-output.txt: Address the concern above.

### FINDING_25: [OUT_OF_SCOPE] Bash state-file value validation is also incomplete
- **Reviewer(s)**: dyn-statefile-hardening-output.txt
- **Severity**: latent
- **Concern**: Bash validates state-file line syntax but lacks value-level charset checks for fields like `BRANCH_NAME` and `PR_URL`; this was not introduced by the branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-statefile-hardening-output.txt: Address the concern above.

### FINDING_26: [OUT_OF_SCOPE] Static review did not run tests or linters
- **Reviewer(s)**: dyn-statefile-hardening-output.txt
- **Severity**: nit
- **Concern**: The reviewer did not execute `make py-test` or `make py-lint`; findings are based on static inspection only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-statefile-hardening-output.txt: Address the concern above.
