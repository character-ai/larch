### [rejected] FINDING_1

**Rejected subtype:** dismissed (0 YES)

### FINDING_1: Mechanical fixed verdicts are excluded from verified accounting
- **Reviewer(s)**: cursor-specialist-correctness, dyn-dyn-runtime-evidence
- **Severity**: major
- **Concern**: `_verified_issue` excludes certifiable `MECH` fixed verdicts, while other report surfaces still count them as fixed, producing inconsistent verified accounting.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-runtime-evidence: Align the three surfaces—either restore `MECH` in `_verified_issue` when the verdict is certifiable, or update SKILL/count semantics so mechanical-only fixed rows are explicitly non-verified.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** dismissed (0 YES)

### FINDING_2: Rename-only test changes are not discovered
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: Test discovery ignores `R*` diff-tree entries, so rename-only changes can result in no pytest execution.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Parse R* diff-tree rows for destination paths under python/tests/, or enable --find-renames in discovery.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** dismissed (0 YES)

### FINDING_6: Runtime git discovery does not set the repository cwd
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: Git discovery and revision commands may run outside `repo_root`, unlike pytest and make invocations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Pass cwd=str(repo_root) on all runtime runner.run calls, including git discovery and rev-parse.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** dismissed (0 YES)

### FINDING_11: Runtime failures overwrite non-certifiable static verdicts
- **Reviewer(s)**: dyn-dyn-runtime-evidence
- **Severity**: major
- **Concern**: `_runtime_overlay` converts negative static verdicts such as `NOT_FIXED` or `REGRESSED` into `SUSPECT`/`RUNTIME`, removing actionable follow-up outcomes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-runtime-evidence: Mirror the promotion guard: only downgrade certifiable fixed verdicts (`CERTIFIABLE_FIXED_VERDICTS`) to runtime `SUSPECT` on failure; for other verdicts keep the static verdict/tier and append bounded runtime failure text to `reason` (or a separate evidence field).


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** dismissed (0 YES)

### FINDING_12: Runtime tests are not bound to the fix SHA contents
- **Reviewer(s)**: dyn-dyn-runtime-evidence
- **Severity**: major
- **Concern**: Tests discovered from `fix_sha` are executed from the current checkout, so runtime evidence may certify different or rewritten test contents.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-runtime-evidence: Either checkout `fix_sha` (or `git worktree`) before pytest, or narrow semantics/docs to “current-main regression of commit-touched tests” and exclude promotion when discovered paths differ from `git show fix_sha:path` checksums.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** dismissed (0 YES)

### FINDING_13: Runtime verification executes non-certifiable static outcomes
- **Reviewer(s)**: dyn-dyn-runtime-evidence
- **Severity**: major
- **Concern**: `runtime_main` requires but does not load the ledger, allowing runtime execution and possible verdict changes for non-certifiable static outcomes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-runtime-evidence: Load `ledger_path`, compute each bundle’s pre-runtime verdict, and skip subprocess execution—or at minimum skip failure downgrade—for non-certifiable static verdicts.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** dismissed (0 YES)

### FINDING_14: Predicate-version bump silently invalidates legacy snapshots
- **Reviewer(s)**: dyn-dyn-runtime-evidence
- **Severity**: minor
- **Concern**: `_previous_snapshot` ignores legacy `run-state.json` files after the predicate-version bump, potentially producing false “First run” or inflated deltas.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-runtime-evidence: Add a compatibility read path for the prior predicate (with documented semantic mapping) or emit an explicit report warning when no compatible predecessor snapshot exists.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0
