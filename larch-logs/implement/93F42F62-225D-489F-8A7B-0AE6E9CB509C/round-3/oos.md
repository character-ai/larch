### FINDING_10: [OUT_OF_SCOPE] Fresh fallback can reset persisted ship loop counters
- **Reviewer(s)**: dyn-resume-state-output.txt, dyn-ci-loop-output.txt
- **Severity**: important
- **Concern**: When ship resume falls back to `start=="fresh"`, persisted CI loop counters can be written and then reset to zero at merge-loop entry, potentially bypassing loop caps after a transient mis-route.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-resume-state-output.txt: When entering the merge loop after a fresh fallback, seed `iteration` / `rebase_count` / `fix_attempts` / `transient_retries` from `resume.*` (the same values already persisted in `ship-pr-state.sh`), or refuse fresh fallback when `PHASE=ci-initial` and counters indicate an in-progress merge loop unless an explicit operator reset flag is set.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_12: [OUT_OF_SCOPE] Corrupt ship resume counters silently reset to zero
- **Reviewer(s)**: dyn-resume-state-output.txt, dyn-ci-loop-output.txt
- **Severity**: important
- **Concern**: `read_resume_counters` maps non-numeric counter values to `0`, which can silently reset budgets from a damaged `ship-pr-state.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-resume-state-output.txt: Treat non-numeric counter fields as a blocked resume (similar to invalid `BRANCH_NAME` / `PR_URL` handling in `_resume_plan`) or emit a loud parse warning and refuse `open-pr` resume until state is repaired.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_14: [OUT_OF_SCOPE] terminal ship failures now always persist PHASE=stalled
- **Reviewer(s)**: dyn-resume-state-output.txt
- **Severity**: latent
- **Concern**: `_write_terminal_state` always writes `PHASE=stalled` on failure, which may remove a `postmerge` signal used by gh-skipped merged detection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-resume-state-output.txt: worth monitoring in forked/`repo_unavailable` runs.


Vote tally: YES=2 NO=1 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_15: [OUT_OF_SCOPE] Restore does not enforce cwd worktree matches --repo
- **Reviewer(s)**: dyn-pr-identity-output.txt, dyn-git-restore-output.txt
- **Severity**: important
- **Concern**: `design-pause-load.sh` reads git snapshots from the caller’s cwd while `--repo` only affects GitHub issue operations, so a repo/worktree mismatch can restore the wrong snapshot or fail misleadingly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-pr-identity-output.txt: After resolving `CURRENT_REPO`, compare it to the slug for `REPO_TOP`’s `origin` (or `git -C "$REPO_TOP" remote get-url origin` normalized) and fail with a dedicated `ERROR=repo-worktree-mismatch` when they diverge; document that restore always uses the cwd worktree, not `--repo`.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_18: [OUT_OF_SCOPE] ship state writer does not validate REPO on write
- **Reviewer(s)**: dyn-pr-identity-output.txt
- **Severity**: latent
- **Concern**: `_write_ship_state()` validates several fields but not `REPO`, allowing corrupt values to persist until later resume validation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-pr-identity-output.txt: worth hardening but not introduced by the pause/resume shell changes.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_19: [OUT_OF_SCOPE] marker-delete failure diagnostics are suppressed
- **Reviewer(s)**: dyn-pr-identity-output.txt
- **Severity**: nit
- **Concern**: `clear_pause_marker` discards `named-block-write.sh` output, so `WARN=marker-delete-failed` lacks the underlying API or command failure reason.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-pr-identity-output.txt: diagnostic emission would help operators without changing control flow.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_22: [OUT_OF_SCOPE] Python ship resume contract documentation is missing or incomplete
- **Reviewer(s)**: dyn-contract-drift-output.txt
- **Severity**: important
- **Concern**: The Python ship-driver resume/state-machine surface expanded without a sibling normative contract documenting resume tokens, persisted counters, merge-signal rules, and output envelopes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-contract-drift-output.txt: Add a `python/ship.md` (or extend `python/README.md` with an explicit resume/state KV section) documenting `ResumePlan.start` values, persisted counter keys, merge-signal thresholds, and stdout/JSON envelope fields; cross-link from SECURITY.md’s Python ship-pr paragraph.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_23: [OUT_OF_SCOPE] committed implement run logs inflate review surface
- **Reviewer(s)**: dyn-contract-drift-output.txt
- **Severity**: nit
- **Concern**: The branch includes a full `larch-logs/implement/…` run tree that is normal `/implement` output but unrelated to pause/resume semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-contract-drift-output.txt: Address the concern above.

Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### FINDING_8: [OUT_OF_SCOPE] Python ship-driver work is bundled with pause/resume changes
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt, dyn-git-restore-output.txt, dyn-contract-drift-output.txt
- **Severity**: important
- **Concern**: The branch includes substantial `python/ship.py` / `python/run_logs.py` work from a separate issue, making pause/resume review scope and regression attribution ambiguous.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Keep pause/resume review scoped to commit 5ccd6e3e8 plus review follow-ups on the nine planned paths.
  - From dyn-contract-drift-output.txt: Split the Python ship resume FSM into its own PR/issue authority (or rebase the pause/resume branch onto `main` without #3448), and keep #3529 to the nine shell/doc/test files the plan names.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_9: [OUT_OF_SCOPE] body-drift docs may overstate marker persistence
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: The body-drift documentation says the marker remains authoritative without clarifying that successful loads delete it afterward.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Clarify that authority applies during validation only; successful install still clears the marker per WI3.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

