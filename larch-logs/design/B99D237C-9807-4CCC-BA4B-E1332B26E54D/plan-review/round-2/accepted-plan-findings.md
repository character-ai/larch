### FINDING_1: Cap-exhaustion test is off by one
- **Reviewer(s)**: Codex-Arch, Codex-Pragmatic, Codex-Requirements, Cursor-dyn-bash-parity, Cursor-dyn-state-file-premises
- **Severity**: important
- **Concern**: Multiple reviewers flagged that the planned `ITERATION=49` with cap `50` immediate-stall test contradicts existing loop semantics, which stall only when `iteration >= cap`; implementing the test as written could remove the final allowed monitor/decide cycle.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Keep existing cap semantics: test immediate stall with ITERATION=50, or expect one monitor call at ITERATION=49 before the next loop stalls.
  - From Codex-Pragmatic: Change the acceptance case to ITERATION=50 for immediate stall, or assert ITERATION=49 performs one monitor pass and then stalls after increment
  - From Codex-Requirements: Keep minimum-change semantics: use ITERATION=50 for immediate stall, or assert ITERATION=49 is restored into the monitor and stalls only after the next wait iteration.
  - From Cursor-dyn-bash-parity: Resume with ITERATION=49 may stall one cycle earlier/later than bash depending on whether the outer loop or decide fires first; the planned test name overstates “immediate.” Align the test with bash: assert stall on the first monitor/decide call only after ITERATION reaches 50, or document intentional double-gate behavior.
  - From Cursor-dyn-state-file-premises: Session-wide cap test should seed/resume with ITERATION=50 (expect stall before monitor), or rename the case to assert one final monitor then stall when ITERATION=49.


### FINDING_2: Open-PR resume state writes can zero restored counters
- **Reviewer(s)**: Cursor-Edge, Cursor-Innovation
- **Severity**: important
- **Concern**: The open-PR resume path can restore counters in memory, then call `_write_ship_state` before the CI loop without passing those counters, overwriting persisted cap progress with zero if a crash or handback occurs before the first counter-preserving CI-loop write.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Thread resume.iteration/rebase_count/fix_attempts/transient_retries through every _write_ship_state on the open-pr path until the CI loop owns updates, or skip counter-bearing state writes until ship.py:545; extend the terminal round-trip test to assert counters survive pr-create writes on second run_ship
  - From Cursor-Innovation: In the open-pr branch, thread resume.iteration/rebase_count/fix_attempts/transient_retries into every _write_ship_state until the CI loop seeds locals, or defer state writes until the loop; add a test that asserts non-zero counters in ship-pr-state.sh immediately after the first open-pr _write_ship_state


### FINDING_3: Merged resume does not refresh postmerge/done ship state
- **Reviewer(s)**: Codex-Edge, Codex-Pragmatic, Codex-dyn-state-file-premises
- **Severity**: important
- **Concern**: The merged-resume branch runs postmerge directly without mirroring the normal state transitions, so `ship-pr-state.sh` can remain at `postmerge` or otherwise stale and later re-entry or finalize restore can treat a completed merge as incomplete.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: In the merged branch, store the postmerge result; when outcome is OK, call _write_ship_state(working, phase="done", with restored counters) before returning, and add a resume test that asserts PHASE=done after successful merged resume
  - From Codex-Pragmatic: Write merged-resume state before postmerge and again on success, matching the normal merge path: _write_ship_state(working, phase="postmerge", restored counters) before run_postmerge_phase and _write_ship_state(working, phase="done", restored counters) after OK
  - From Codex-dyn-state-file-premises: Mirror the normal path in the merged resume branch: capture the postmerge result, call _write_ship_state(working, phase="done") on success, then return the ShipResult


### FINDING_4: Repo-unavailable ensure_pr can erase restored PR identity
- **Reviewer(s)**: Codex-Pragmatic, Codex-dyn-bash-parity, Codex-dyn-state-file-premises
- **Severity**: important
- **Concern**: On repo-unavailable open-PR resumes, restored `PR_NUMBER`/`PR_URL` can be validated from state but then overwritten when `ensure_pr` returns local-only empty identity values.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Preserve resumed identity when ensure_pr returns local-only or empty: on resume.start == "open-pr", set pr_number=ensured.number or resume.pr_number and pr_url=ensured.url or resume.pr_url
  - From Codex-dyn-bash-parity: For repo_unavailable, honor bash's state PHASE skip semantics before PR identity, or exclude repo_unavailable from open-pr resume and preserve the current local-only flow. Never let ensure_pr overwrite a restored PR identity with 0.
  - From Codex-dyn-state-file-premises: Preserve resume.pr_number and resume.pr_url when ensure_pr returns an empty local-only result, or skip ensure_pr for repo_unavailable open-pr resume after the required gates and write the hydrated done state


### FINDING_5: No-state resume can classify as open-pr from argv/env
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Concern**: The plan says missing `ctx.state_file` should mean fresh, but `_resume_plan` can still classify as open-pr using `ctx.pr_number`, skipping checks/postbump without durable state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: In _resume_plan, short-circuit to fresh when ctx.state_file is falsy; only use ctx.pr_number as fallback after a state file exists but lacks PR_NUMBER, or remove that fallback


### FINDING_6: Resume can bypass actual branch/head validation
- **Reviewer(s)**: Codex-Requirements, Codex-dyn-state-file-premises
- **Severity**: important
- **Concern**: Non-fresh resume classification can rely on stale context or state/manifest data instead of verifying the actual checked-out branch and PR head, allowing open-pr or merged resume work to proceed on the wrong checkout.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add a minimal git.try_current_branch probe in _resume_plan; require it to match the expected branch and PR head when available, otherwise classify fresh so existing guards run.
  - From Codex-dyn-state-file-premises: Apply the same current-branch match before accepting merged resume from state, manifest, or gh head_ref; if it mismatches, return fresh


### FINDING_7: Terminal monitor handback can lose consumed counter increments
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: Terminal CI handbacks can persist only pre-monitor loop locals, losing increments caused by terminal `ci_monitor` results such as `did_fixing=True`, which can bypass session-wide caps on re-entry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: When writing terminal state for the ci_monitor non-OK path, persist the live counters plus the same monitor.did_fixing and monitor.transient_rerun_attempted increments used on the OK continue path; add a focused round-trip test for terminal did_fixing.


### FINDING_9: PHASE=done lacks idempotent fast path
- **Reviewer(s)**: Cursor-dyn-bash-parity
- **Severity**: important
- **Concern**: A completed `PHASE=done` state can still classify as open-pr and re-enter CI when the PR remains open, instead of returning success idempotently like bash.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-bash-parity: Spurious re-invocation after a successful PR-only run repeats CI/merge work instead of idempotent exit 0. Add a first-class done target (or treat PHASE=done as immediate ShipResult OK) before PR-identity/open-pr logic.


### FINDING_12: Manifest DONE can prematurely force merged resume
- **Reviewer(s)**: Cursor-dyn-bash-parity
- **Severity**: latent
- **Concern**: Treating `manifest_status == DONE` alone as merged can route to postmerge while the persisted phase or gh state still indicates active CI/open PR, unlike bash’s PHASE-driven routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-bash-parity: Premature manifest DONE (partial postmerge, manual edit) routes to run_postmerge_phase while CI is still active in bash. Restrict manifest DONE to merged only when PHASE is postmerge/done or PR_CLOSED/MERGE_RESULT already agree; otherwise ignore manifest for routing.


### FINDING_13: Rebase-continuation handback phase is dropped
- **Reviewer(s)**: Codex-dyn-bash-parity
- **Severity**: important
- **Concern**: The proposed resume flow does not handle bash’s explicit `ship-pr-rrr-phase14` rebase-continuation path, so non-bump conflict handbacks can skip the required `run_rebase_rebump` continuation and counter update.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-bash-parity: Handle RESUME_PHASE=ship-pr-rrr-phase14 before the coarse fresh/open-pr/merged decision, or refuse that resume shape until Python supports it. Keep the change narrow and add only this parity test.


### FINDING_14: Python cap check runs before bash pass/already-merged decisions
- **Reviewer(s)**: Codex-dyn-bash-parity
- **Severity**: important
- **Concern**: Preserving Python’s outer pre-monitor iteration-cap check can stall at the cap before observing CI pass or already-merged outcomes, while bash evaluates pass/already-merged before safety caps.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-bash-parity: Move/remove the run_ship pre-monitor cap and rely on ci_monitor.decide's bash-order cap for non-merge actions. Update the planned tests to cover pass-at-cap plus non-merge cap exhaustion.### OOS_1:
- **Description**: Three new `monitor()` outcome tests are unrelated to ship resume/counter restore. Scenario: The SIMPLE plan’s core fix is `run_ship()` resume + terminal counter threading; `test_ship.py` already stubs `ci_monitor.monitor` for handback/cap cases. Adding monitor bail/transient/local-unfixable coverage expands scope (~60+ lines) without exercising new resume code.
- **Reviewer**: Cursor-Arch
- **Severity**: nit
- **Focus area**: architecture
- **Location**: python/test_ci_monitor.py:80-84
- **Phase**: design


