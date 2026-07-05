### FINDING_1: Bind `REPO_ROOT` before guideline helpers
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: blocking
- **Concern**: Gate C and Step 1d.7 invoke guideline helpers from fresh Bash fences while relying on `$REPO_ROOT` that is not rebound in-fence, so `present-note` / `persist-design-assessment` can still resolve as if the repo were absent and silently skip the assessment.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In each Presentation/persist helper Bash fence, read REPO_ROOT from $DESIGN_TMPDIR/source-env.sh (or source current-design-env-$PPID.sh) before the first present-note/persist call; keep the planned empty-root repair stop
  - From Cursor-Innovation: Before the first guideline helper in each gate, load the Step 0 capture: source `$DESIGN_TMPDIR/source-env.sh` in the same Bash fence, or emit `REPO_ROOT=` from `step0_session_main` stdout and require a repair stop when it is empty before any helper call. Do not rely on `session read-key` against `source-env.sh` as written today; lines use an `export` prefix.
  - From Cursor-Pragmatic: Add a binding step before every guideline helper call: read REPO_ROOT from $DESIGN_TMPDIR/source-env.sh via session read-key (or source that file once), then apply the existing repair-stop when empty; mirror the same pattern in design-outline.md.
  - From Cursor-Requirements: Require each guideline helper fence to source $DESIGN_TMPDIR/source-env.sh first (or inline-read REPO_ROOT from that file) before present-note / persist-design-assessment; keep the empty-REPO_ROOT repair stop after binding.

### FINDING_2: Parse quoted `REPO_ROOT` exports correctly
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: REPO_ROOT recovery must parse shlex-quoted exports, not mirror the bool regex. Scenario: _export_line writes export REPO_ROOT via shlex.quote; a bool-style ^export REPO_ROOT=...$ regex will not recover quoted paths, so init_runparams refresh can still drop REPO_ROOT and re-open the clobber path
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Implement _recover_prior_path using parse_allowlisted_env_line (or equivalent shlex split) and wire it into write-design-env when --repo-root is absent

### FINDING_3: Gate C regression must cover the persistence contract
- **Reviewer(s)**: Codex-Arch, Codex-Requirements
- **Severity**: important
- **Concern**: The planned test only exercises helper return codes and can miss the skip-approve Gate C contract, so the flow could still omit the bounded warning or advance to auto-approval/Step 5 after a failed persist.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Revise the planned regression to pin the Gate C branch itself. Exercise an available Gate C harness, or add a narrow markdown contract test if no executable harness exists, that verifies the skip-approve branch runs `present-note --repo-root "$REPO_ROOT"` and `persist-design-assessment --repo-root "$REPO_ROOT"`, writes the assessment artifact, and stops with the bounded warning on forced persist failure.
  - From Codex-Requirements: Add a focused regression or validation step that exercises the Gate C non-zero persistence branch and asserts the bounded warning is recorded and the flow does not prompt, auto-approve, or transition to Step 5

### FINDING_4:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/larch/design/design_step0.py:UPDATED
- **Concern**: [SCOPE-REDUCTION] New Step 0 git rev-parse helper duplicates consumer_repo_root. Scenario: larch.git.repo_roots.consumer_repo_root already resolves the consumer git toplevel from cwd via the same rev-parse contract; a second resolver drifts if flags or fallbacks change
- **Proposed resolution**: Resolve the root with consumer_repo_root() (or proc.run wrapper around it) and pass str(root) to write-design-env --repo-root; do not add a parallel helper

### FINDING_5:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/larch/git/pr_body.py:457-464; python/larch/state/_report.py:154-166
- **Concern**: [SCOPE-REDUCTION] Firm version-fallback edits are outside the assessment-persistence acceptance criteria. Scenario: The issue acceptance criteria require assessment artifact presence and fail-closed Gate C behavior only; wrong _plugin_version_local path is a separate reporting defect (wrong Path parents), not required to stop cwd-based guideline absence
- **Proposed resolution**: Remove pr_body.py, _report.py, and test_pr_body.py from firm UPDATED scope; keep the REPO_ROOT/threading work only

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/larch/git/pr_body.py:457-464
- **Concern**: [SCOPE-REDUCTION] Version-fallback edits are outside acceptance criteria. Scenario: The issue requires assessment persistence and fail-closed Gate C behavior. `pr_body.py` and `_report.py` version lookup fixes are a separate symptom (wrong path under `python/larch/`) and do not restore `architectural-guideline-assessment.md` when repo root was wrong. Keeping them expands diff and test surface without clearing a stated acceptance gate.
- **Proposed resolution**: Drop `python/larch/git/pr_body.py`, `python/larch/state/_report.py`, and `python/tests/git/test_pr_body.py` from firm scope; file a follow-up if version display still matters.

### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: python/larch/design/design_step0.py:161-187
- **Concern**: [SCOPE-REDUCTION] New Step 0 repo-root helper duplicates `consumer_repo_root`. Scenario: The plan adds a new git rev-parse helper in `design_step0.py`, but `larch.git.repo_roots.consumer_repo_root` already resolves the consumer git toplevel from cwd for design flows. Two resolvers drift on fallback and subprocess conventions.
- **Proposed resolution**: In `design_step0.py`, call `consumer_repo_root()` (with `Path.cwd().resolve()` only when git returns `None`) and pass that to `write-design-env --repo-root`; do not add a parallel resolver.

### FINDING_8:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/larch/git/pr_body.py:457-464; python/larch/state/_report.py:154-166
- **Concern**: [SCOPE-REDUCTION] Drop the Larch-version fallback work from this PR. Scenario: The acceptance criteria require Gate C assessment persistence and warnings. The firm pr_body.py, _report.py, and related test changes fix a separate reporting symptom already classified out of scope, increasing diff and review surface without closing the assessment hole.
- **Proposed resolution**: Remove the pr_body.py, _report.py, and version-fallback test bullets from the plan. File or keep a separate tracked issue for the version fallback.

### FINDING_9:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/larch/design/design_step0.py
- **Concern**: [SCOPE-REDUCTION] New Step 0 git rev-parse helper duplicates consumer_repo_root. Scenario: The plan adds a separate resolver in design_step0.py, but larch.git.repo_roots.consumer_repo_root already resolves the consumer git toplevel from cwd and is used by design_step2b, design_publish, and design_postplan. Two resolvers can drift on fallback and subprocess conventions.
- **Proposed resolution**: Call consumer_repo_root(Path.cwd()) at Step 0, fall back to Path.cwd().resolve() only when it returns None, and pass that value to write-design-env --repo-root; do not add a parallel git helper.

### FINDING_10:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/larch/git/pr_body.py:457-464
- **Concern**: [SCOPE-REDUCTION] Firm version-fallback edits are outside acceptance criteria. Scenario: The issue acceptance criteria cover assessment persistence and fail-closed Gate C only. pr_body.py _plugin_version_local and _report.py version fallback are correlated telemetry on the same runs but not required to fix the skip-approve assessment bug; they add ~2 modules and tests unrelated to REPO_ROOT threading.
- **Proposed resolution**: Remove python/larch/git/pr_body.py and python/larch/state/_report.py from firm UPDATED scope for this PR; track version fallback separately or mark MAY_UPDATE if desired.

### FINDING_11:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: nit
- **Focus area**: architecture
- **Location**: python/larch/design/design_step0.py
- **Concern**: [SCOPE-REDUCTION] New Step 0 repo-root resolver duplicates consumer_repo_root. Scenario: larch.git.repo_roots.consumer_repo_root already resolves the consumer git toplevel from cwd via git -C rev-parse. A second rev-parse helper in design_step0.py adds drift risk for the same contract.
- **Proposed resolution**: Resolve the Step 0 root with consumer_repo_root() (plus the plan's Path.cwd() fallback only when git returns None) and pass that value to write-design-env --repo-root.
