### [Plan Review] FINDING_4

### FINDING_4: Atomic finalize-state writer ownership may remain duplicated
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The plan risks mirroring rather than moving `_write_finalize_text_safely`; duplicated atomic-write logic between finalize and session-state code can diverge and weaken symlink/O_EXCL guarantees.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Duplicated atomic-write logic can diverge from ship finalize-state writes and weaken symlink/O_EXCL guarantees Move _write_finalize_text_safely into session_env.py with write_finalize_state_merged; import back from finalize.py


### [Plan Review] FINDING_5

### FINDING_5: `read-workflow-path.sh` fallback would be lost after deleting `read-design-classification.sh`
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-dyn-emitter-routing-fidelity
- **Severity**: important
- **Concern**: The cutover deletes `read-design-classification.sh` but does not explicitly replace `read-workflow-path.sh`’s `-x` fallback probe; timing/report callers may classify artifacts as `unknown` instead of preserving current `SIMPLE|HARD` fallback behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add scripts/read-workflow-path.sh under Files to modify: replace the dirname probe with python3 …/cli.py session read-classification (preserve HARD-default-on-invalid behavior, not only SIMPLE|HARD stdout)
  - From Cursor-dyn-emitter-routing-fidelity: Replace the `-x` dirname probe with a call to `python3 …/cli.py session read-classification "$f"` (or resolve CLI via `SCRIPT_DIR`/plugin root), swallow stderr, and accept `SIMPLE|HARD` like the current branch; document this explicitly in the call-site cutover section
  - From Cursor-dyn-emitter-routing-fidelity: Replace the `-x` bash probe with `python3 …/cli.py session read-classification "$f"` (resolve CLI via `SCRIPT_DIR`/plugin root), keep `2>/dev/null || true`, and accept only `SIMPLE|HARD`; add one line to the call-site cutover bullet for `read-workflow-path.sh`


### [Plan Review] FINDING_6

### FINDING_6: Token-propagation harness still invokes retired session scripts
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The call-site cutover misses `test-implement-review-token-propagation.sh`, which still invokes `session-setup.sh` and `read-session-env-key.sh`; deleting absorbed bash scripts can make the harness or nested-review CI paths fail at script-not-found.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Explicitly add this harness to the grep-driven cutover (session setup/read-key CLI paths) or fold its assertions into python/test_session_env.py and drop the bash harness in the same Makefile/agent-lint pass


### [Plan Review] FINDING_8

### FINDING_8: `write-design-env` allowlist omits required source-env keys
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: The planned guarded `write-design-env` allowlist omits keys that current design env output always or conditionally writes, so normal `/design` rehydration output could be rejected or lose required keys.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add DESIGN_TMPDIR, SESSION_TMPDIR, SESSION_ID, and CLAUDE_PLUGIN_ROOT to the write-design-env allowlist, and cover a normal guarded source-env write containing those keys in test_session_env.py


### [Plan Review] FINDING_10

### FINDING_10: `test-implement-finalize.sh` stubs stale bash paths after session CLI cutover
- **Reviewer(s)**: Cursor-dyn-call-site-cutover-gaps
- **Severity**: important
- **Concern**: The plan omits retargeting the implement-finalize integration harness; after production code invokes `python3 …/cli.py session …`, the harness’s bash stubs for cleanup/read-key scripts will no longer exercise the real cutover path and assertions can rot.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-call-site-cutover-gaps: Add an explicit plan step to retarget `test-implement-finalize.sh` (and peers below) to stub or fixture the `session` CLI path the cutover script will actually exec


### [Plan Review] FINDING_12

### FINDING_12: `ship.py` duplicate tmpdir allowed-root helper remains outside shared ownership
- **Reviewer(s)**: Codex-dyn-finalize-boundary
- **Severity**: latent
- **Concern**: The plan moves tmpdir path-safety ownership from `finalize.py` but misses `ship.py`’s duplicate allowed-root logic, so the stated single-owner contract would not be achieved and future root fixes could diverge.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-finalize-boundary: Add an explicit ship.py update: make _tmpdir_under_allowed_root delegate to the new session_env shared allowed-root helper, or remove the duplicate wrapper if callers can use the shared helper directly.


### [Plan Review] FINDING_14

### FINDING_14:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: code-quality
- **Location**: plan.txt:121
- **Concern**: [SCOPE-REDUCTION] Stale-reference sweep says ALL tracked files even though retired-script lint excludes larch-logs and CHANGELOG. Scenario: Implementer may churn historical larch-logs references that are intentionally excluded by python/migration_lint.py and docs/python-migration.md, creating unnecessary scope and merge risk
- **Proposed resolution**: Limit the sweep to lint-retired-scripts scanned files: exclude larch-logs, CHANGELOG.md, and the manifest itself


