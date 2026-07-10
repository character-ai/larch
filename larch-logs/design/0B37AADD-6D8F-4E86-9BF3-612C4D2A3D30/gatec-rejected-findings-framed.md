---LARCH-REJECTED-BEGIN---
## Considered Plan Review Suggestions (Not Adopted)

These reviewer suggestions were considered but not adopted. Some may already be addressed by the current plan; they are not automatically unimplemented gaps.

### [Plan Review] FINDING_4

### FINDING_4: Probe live same-run bgjobs before teardown kills them
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Concern**: Finalization may kill session background processes before checking whether an exact-run registry entry is live. The subsequent preservation check then observes dead work and clears the active pointer during a race where same-run background work should preserve it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Run the exact-run, in-budget registry preservation probe before kill_session_background_processes, skip compare-and-clear deactivation when preservation applies, then kill and delete tmpdir; cover this ordering in test_finalize.py.


### [Plan Review] FINDING_5

### FINDING_5: Clear stale progress before setup and reviewer probes
- **Reviewer(s)**: Cursor-Innovation, Codex-Requirements
- **Severity**: major
- **Concern**: The pinned Step 0 ordering allows session setup, preflight, or reviewer probes to run while the previous run remains active. If those steps block or fail, stale status remains visible during the new-run startup window.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Move unconditional stale-pointer removal to the first Step 0 action (before `session setup`), then keep resolve/persist/activate immediately after setup returns a session id and before reviewer probing.
  - From Codex-Requirements: Pin one unambiguous order for both flows: capture and compare-clear the prior pointer first, then create or load session state, persist and activate the effective run ID, probe reviewers, persist probe results, write the environment, and route degraded tools.


### [Plan Review] FINDING_6

### FINDING_6: Use a dedicated entry clear instead of compare-clearing against the new run ID
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Concern**: At Step 0 entry, the new effective run is not yet the active pointer. Calling `deactivate_run` with that new ID can no-op, leaving the previous run active and its statusline breadcrumb visible.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Define entry stale-clear separately: read `current` (or unconditional unlink) and deactivate that id, or add a dedicated clear-active helper; reserve compare-and-clear only for lifecycle/SessionStart/finalize callers that own a specific run id.


### [Plan Review] FINDING_9

### FINDING_9:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/report/statusline.py:24-25
- **Concern**: [SCOPE-REDUCTION] Keep source=clear out of session reset sources. Scenario: The bound bug is stale status at Claude startup and job entry; treating source=clear like startup deletes current after Step 0 activation while early foreground steps still write via append_breadcrumb, silencing the statusline for the rest of an active run until re-activation
- **Proposed resolution**: Limit RESET_SESSION_SOURCES to explicit startup only (drop clear), adjust docs and tests accordingly, and rely on early Step 0 clear plus run-matched deactivate for stale cleanup ### 1. Design run ID persistence writer missing (correctness / architecture) The plan requires every design lifecycle path to resolve a persisted effective `LARCH_RUN_ID`, but the only durable design session writer today is `session write-design-env`, and its allowlist omits `LARCH_RUN_ID`: WRITE_DESIGN_ENV_KEYS = frozenset({ "DESIGN_TMPDIR", "SESSION_TMPDIR", "SESSION_ID", "REPO", "REPO_ROOT", "ISSUE_NUMBER", ... }) Round 1 **FINDING_4** is not fully closed until `session_env.py` is in the firm file list and `write-design-env` emits `LARCH_RUN_ID`. Without that, custom `--run-id` activation cannot survive rehydration in `design_pause.py`, `design_terminal.py`, `plan_review.py`, or bgjob start. ### 2. Source-env refresh paths can wipe the run ID (correctness) Even if Step 0a writes `LARCH_RUN_ID`, Step 0b still rewrites `source-env.sh` without it in `design_router.init_runparams_main` and `_refresh_resume_source_env` in `design_step0.py`. Those refresh paths are absent from the plan’s firm file list, so the persisted identity can disappear before terminal cleanup runs. ### 3. Step 6 live Step 5c guard breaks after bgjob identity change (correctness / risk-integration) The plan requires “do not deactivate when Step 5c work remains live,” but `_step6_in_flight` still calls `registry.read_for(tmpdir=..., step=...)` with no run ID: reg_path, entry = registry.read_for(tmpdir=design_tmpdir, step=DESIGN_BGJOB_STEP5C) if entry is None: return False if registry.child_liveness(entry).live or registry.daemon_liveness(entry).live: After bgjob rows store the persisted UUID/custom run ID instead of the tmpdir hash, this check can falsely report “not in flight” and allow premature deactivation plus tmpdir deletion. ### 4. [SCOPE-REDUCTION] `source=clear` should not reset active foreground runs (correctness) The plan keeps `clear` in `RESET_SESSION_SOURCES` alongside `startup`. The issue scope targets stale status at **startup** and **new job entry**, not every SessionStart clear during an active run. Mid-session `clear` after Step 0 activation removes `current` while pre-bgjob foreground work still depends on `append_breadcrumb`, which no-ops without `current`. Early Step 0 pointer clear plus run-matched deactivate already address the reported bug without expanding reset sources.


### [Plan Review] FINDING_10

### FINDING_10:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/report/statusline.py:24-25
- **Concern**: [SCOPE-REDUCTION] Keeping source=clear in RESET_SESSION_SOURCES can silence active foreground runs. Scenario: The bound issue targets stale status at Claude start and new job entry, not mid-session context clears. After Step 0 activates current, many pre-bgjob steps still write through append_breadcrumb, which no-ops once current is removed. A SessionStart clear with no run-matched live bgjob will compare-and-clear the active run and leave the statusline blank for the rest of that run.
- **Proposed resolution**: Limit RESET_SESSION_SOURCES to startup only, or treat clear as a no-op like resume/compact. Drop clear-specific reset tests and doc bullets if startup-only.


---LARCH-REJECTED-END---
