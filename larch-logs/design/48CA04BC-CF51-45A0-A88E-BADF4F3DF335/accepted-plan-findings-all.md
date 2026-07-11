### FINDING_1: Salvage reconciliation bypasses mutation authorization
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-Mutation Boundary Auditor
- **Severity**: major
- **Concern**: `_reconcile_post_recovery_comment` and related salvage reconciliation paths perform direct `gh` comment, close, and view operations outside the guarded filing choke points. Tests, development replays, or unauthorized runs can therefore mutate real report issues even when `issue create-one` and `file-failure-report-cross-repo.sh` refuse.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Gate _reconcile_post_recovery_comment the same way as filing: validate live-run authorization from source-env.sh before any gh mutation, refuse with bounded local audit on failure, and add a focused regression that reconcile without authorization emits zero gh calls.
  - From Cursor-Innovation: In design_terminal.py, run the same fail-closed mutation authorization check (using source-env.sh) at the start of _reconcile_post_recovery_comment and _reconcile_failed_publish_tail_report before any gh call. On refusal, keep the existing reconcile-failed path and leave the report open. Add a design lifecycle regression that exercises salvage reconciliation without monkeypatching _reconcile_post_recovery_comment and proves zero gh invocations.
  - From Cursor-Pragmatic: In design_terminal.py gate _reconcile_post_recovery_comment on the same session-backed authorization read from $DESIGN_TMPDIR/source-env.sh before any gh call; on refusal record reconcile-failed locally and skip mutations. Add a test_design_lifecycle regression that drives reconciliation without authorization and asserts zero gh calls.
  - From Cursor-Requirements: In `design_terminal.py`, require the same live-mutation authorization check (from guarded `source-env.sh`) immediately before any salvage `gh` call; on refusal skip comment/close and record a bounded fallback reason, matching Tier A refusal handling.
  - From Cursor-dyn-Mutation Boundary Auditor: Add the same fail-closed mutation-auth check (validated `source-env.sh` or explicit operator route) at the start of `_reconcile_post_recovery_comment` and `_reconcile_failed_publish_tail_report`; on refusal skip comment/close and keep existing reconcile-failed audit behavior


### FINDING_2: Design issue callers lack session authorization wiring
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic
- **Severity**: major
- **Concern**: Live `/design` child paths invoke `/larch:issue` and nested `create-one` calls without forwarding the session-backed authorization context. After the gate lands, Step 0b, Step 5b, and decomposition partition filing can refuse and block legitimate tracking, OOS, and partition filing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add session-backed wiring: update skills/issue/SKILL.md to accept a session context file when DESIGN_TMPDIR/source-env.sh exists, and update skills/design/SKILL.md Step 0b, finalize-step5.md Step 5b, and decompose-panel.md /larch:issue invocation to pass that context. List those files under Files to modify/create.
  - From Cursor-Pragmatic: Add skills/design/references/finalize-step5.md and skills/design/references/decompose-panel.md to Files to modify/create. Forward $DESIGN_TMPDIR/source-env.sh into every /larch:issue invocation and into each nested create-one argv. Extend skills/issue/SKILL.md with a session-backed branch distinct from operator-invoked filing.


### FINDING_5: Dry-run is not fully offline
- **Reviewer(s)**: Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-Mutation Boundary Auditor
- **Severity**: major
- **Concern**: `issue create-one --dry-run` resolves repositories and/or validates labels before returning, which can invoke `gh repo view` or `gh label list`. This violates the required zero-`gh` dry-run contract and permits network access without authorization.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Short-circuit dry-run immediately after title redaction and authorization parsing, before _resolve_repo, _valid_labels, temp body writes, or any gh subprocess. Pin the no-gh dry-run behavior in test_issue_create.py.
  - From Codex-Innovation: Add an unconditional dry-run branch that skips label lookup, or gate label validation behind not dry_run; preserve the existing dry-run label output contract as needed
  - From Cursor-Pragmatic: Hoist the dry-run branch immediately after title redaction and before repo resolution, label validation, and body reads that are only needed for live create. Pin the no-gh dry-run contract in python/tests/issue/test_issue_create.py with a stub gh log.
  - From Cursor-Requirements: In `issue_create.py`, return the dry-run envelope immediately after title redaction (or after parsing only), before repo resolution, label validation, temp body creation, and create paths; keep label/repo resolution offline for dry-run previews.
  - From Cursor-dyn-Mutation Boundary Auditor: In `issue_create.py`, branch on `dry_run` immediately after parse/redact and return preview KVs before `_resolve_repo`, `_valid_labels`, temp-body creation, or any `gh` invocation


### FINDING_6: `audit-runs close-priors` remains ungated
- **Reviewer(s)**: Codex-Arch, Codex-dyn-Mutation Boundary Auditor
- **Severity**: major
- **Concern**: The dev-only `audit-runs close-priors` flow can list, comment on, and close real audit issues without the explicit authorization marker.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add the same fail-closed authorization contract to `close-priors`, pass the explicit operator context from `.claude/skills/audit-runs/SKILL.md`, and cover unauthorized subprocess execution with zero `gh` calls.
  - From Codex-dyn-Mutation Boundary Auditor: Add the explicit operator-invoked authorization input and fail-closed check to `close_priors_main` before the first GitHub operation. Thread it from `.claude/skills/audit-runs/SKILL.md`, and preserve refusal as a distinct status without attempting comment or close operations.


### FINDING_7: OOS filing has direct mutation paths outside the guarded boundary
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Concern**: OOS filing performs direct GitHub operations for blocker probes, label creation and edits, and failed-create cleanup. These paths can query or mutate real issues even when the guarded `create-one` boundary refuses.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Require and validate the active mutation context before these direct `gh` and cleanup paths, propagate it through the OOS filing flow, and add coverage proving unauthorized OOS execution makes zero GitHub calls.


### FINDING_11: Reporter performs GitHub calls before authorization refusal
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Concern**: Tier A reporter execution can perform pre-helper `gh repo view` calls before the guarded filing helper refuses, violating the requirement that unauthorized realistic reporter fixtures invoke neither the helper nor `gh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add an explicit reporter-level authorization check before repository resolution and helper invocation, or move repository resolution behind a shared guarded boundary. Cover both `/design` and `/implement` Tier A paths.


### FINDING_12: Normalizer does not allow the new refusal status
- **Reviewer(s)**: Cursor-dyn-Mutation Boundary Auditor
- **Severity**: major
- **Concern**: The normalizer allowlist omits the new refusal status, and the plan does not specify mapping it to `fallback-print-required` while preserving the designated fallback reason or preventing terminal filing from continuing.
- **Suggested revisions (informational for voters; coder decides):**


### FINDING_13: Operator `/issue` documentation does not pass explicit authorization
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: minor
- **Concern**: The operator `/issue` skill is marked as authorized, but its illustrated `issue create-one` commands omit the explicit authorization argument or context file required for non-session callers. The same gap may affect the audit skill command examples.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add the exact operator-invoked flag or `--live-mutation-context-file` example to the `issue create-one` command blocks in `skills/issue/SKILL.md` and `.claude/skills/audit-runs/SKILL.md`, using the literals defined in `config.py`.


### FINDING_6: Tier-A dedup performs GitHub work before authorization gate
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Concern**: `file_tier_a_after_compose` calls `dedup_tier_a_report_main` with only `helper_common()` args. `dedup_tier_a_report` then runs `gh repo view` and a `--dedup-only` helper lookup before any mutation-context argument exists. Unauthorized design failure-report fixtures that reach the dedup branch can still hit `gh` even when create filing is gated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Name `dedup_tier_a_report` in the plan; require mutation-context validation at its entry before repo resolution or helper invocation; pass `$DESIGN_TMPDIR/source-env.sh` (and the implement equivalent) through the dedup argv; assert zero `gh` calls on refusal in `test_design_lifecycle.py` / `test_stall_recovery.py`.


### FINDING_10:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: architecture
- **Location**: Plan Goal section
- **Concern**: [SCOPE-REDUCTION] Goal claims coverage of every known issue-mutation path while firm files omit several live surfaces. Scenario: Binding issue acceptance only requires filing choke-point refusal plus reporter regression; keeping the broad Goal without `tracking_issue.py`, `decompose.py` close-original, or `clarify.py` updates either over-scopes the 865-line plan or leaves a false completeness claim
- **Proposed resolution**: Narrow the Goal to the binding acceptance surfaces explicitly listed in approach steps 3-9, or add firm `### UPDATED:` rows for each remaining live mutation module before claiming full-path coverage


