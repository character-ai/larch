### [Plan Review] FINDING_4

### FINDING_4:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/larch/design/design_step0.py:UPDATED
- **Concern**: [SCOPE-REDUCTION] New Step 0 git rev-parse helper duplicates consumer_repo_root. Scenario: larch.git.repo_roots.consumer_repo_root already resolves the consumer git toplevel from cwd via the same rev-parse contract; a second resolver drifts if flags or fallbacks change
- **Proposed resolution**: Resolve the root with consumer_repo_root() (or proc.run wrapper around it) and pass str(root) to write-design-env --repo-root; do not add a parallel helper


### [Plan Review] FINDING_5

### FINDING_5:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/larch/git/pr_body.py:457-464; python/larch/state/_report.py:154-166
- **Concern**: [SCOPE-REDUCTION] Firm version-fallback edits are outside the assessment-persistence acceptance criteria. Scenario: The issue acceptance criteria require assessment artifact presence and fail-closed Gate C behavior only; wrong _plugin_version_local path is a separate reporting defect (wrong Path parents), not required to stop cwd-based guideline absence
- **Proposed resolution**: Remove pr_body.py, _report.py, and test_pr_body.py from firm UPDATED scope; keep the REPO_ROOT/threading work only


### [Plan Review] FINDING_6

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/larch/git/pr_body.py:457-464
- **Concern**: [SCOPE-REDUCTION] Version-fallback edits are outside acceptance criteria. Scenario: The issue requires assessment persistence and fail-closed Gate C behavior. `pr_body.py` and `_report.py` version lookup fixes are a separate symptom (wrong path under `python/larch/`) and do not restore `architectural-guideline-assessment.md` when repo root was wrong. Keeping them expands diff and test surface without clearing a stated acceptance gate.
- **Proposed resolution**: Drop `python/larch/git/pr_body.py`, `python/larch/state/_report.py`, and `python/tests/git/test_pr_body.py` from firm scope; file a follow-up if version display still matters.


### [Plan Review] FINDING_7

### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: python/larch/design/design_step0.py:161-187
- **Concern**: [SCOPE-REDUCTION] New Step 0 repo-root helper duplicates `consumer_repo_root`. Scenario: The plan adds a new git rev-parse helper in `design_step0.py`, but `larch.git.repo_roots.consumer_repo_root` already resolves the consumer git toplevel from cwd for design flows. Two resolvers drift on fallback and subprocess conventions.
- **Proposed resolution**: In `design_step0.py`, call `consumer_repo_root()` (with `Path.cwd().resolve()` only when git returns `None`) and pass that to `write-design-env --repo-root`; do not add a parallel resolver.


### [Plan Review] FINDING_8

### FINDING_8:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/larch/git/pr_body.py:457-464; python/larch/state/_report.py:154-166
- **Concern**: [SCOPE-REDUCTION] Drop the Larch-version fallback work from this PR. Scenario: The acceptance criteria require Gate C assessment persistence and warnings. The firm pr_body.py, _report.py, and related test changes fix a separate reporting symptom already classified out of scope, increasing diff and review surface without closing the assessment hole.
- **Proposed resolution**: Remove the pr_body.py, _report.py, and version-fallback test bullets from the plan. File or keep a separate tracked issue for the version fallback.


### [Plan Review] FINDING_9

### FINDING_9:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/larch/design/design_step0.py
- **Concern**: [SCOPE-REDUCTION] New Step 0 git rev-parse helper duplicates consumer_repo_root. Scenario: The plan adds a separate resolver in design_step0.py, but larch.git.repo_roots.consumer_repo_root already resolves the consumer git toplevel from cwd and is used by design_step2b, design_publish, and design_postplan. Two resolvers can drift on fallback and subprocess conventions.
- **Proposed resolution**: Call consumer_repo_root(Path.cwd()) at Step 0, fall back to Path.cwd().resolve() only when it returns None, and pass that value to write-design-env --repo-root; do not add a parallel git helper.


### [Plan Review] FINDING_10

### FINDING_10:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/larch/git/pr_body.py:457-464
- **Concern**: [SCOPE-REDUCTION] Firm version-fallback edits are outside acceptance criteria. Scenario: The issue acceptance criteria cover assessment persistence and fail-closed Gate C only. pr_body.py _plugin_version_local and _report.py version fallback are correlated telemetry on the same runs but not required to fix the skip-approve assessment bug; they add ~2 modules and tests unrelated to REPO_ROOT threading.
- **Proposed resolution**: Remove python/larch/git/pr_body.py and python/larch/state/_report.py from firm UPDATED scope for this PR; track version fallback separately or mark MAY_UPDATE if desired.


### [Plan Review] FINDING_11

### FINDING_11:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: nit
- **Focus area**: architecture
- **Location**: python/larch/design/design_step0.py
- **Concern**: [SCOPE-REDUCTION] New Step 0 repo-root resolver duplicates consumer_repo_root. Scenario: larch.git.repo_roots.consumer_repo_root already resolves the consumer git toplevel from cwd via git -C rev-parse. A second rev-parse helper in design_step0.py adds drift risk for the same contract.
- **Proposed resolution**: Resolve the Step 0 root with consumer_repo_root() (plus the plan's Path.cwd() fallback only when git returns None) and pass that value to write-design-env --repo-root.


