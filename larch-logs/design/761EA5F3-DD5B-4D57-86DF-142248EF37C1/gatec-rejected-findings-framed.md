---LARCH-REJECTED-BEGIN---
## Considered Plan Review Suggestions (Not Adopted)

These reviewer suggestions were considered but not adopted. Some may already be addressed by the current plan; they are not automatically unimplemented gaps.

### [Plan Review] FINDING_1

### FINDING_1: Cursor lint-fix must preserve auth-export behavior without config-context isolation
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: Descriptor adoption could enable Cursor configuration-context isolation that the current lint-fix path does not use, changing authentication, temporary configuration, and cleanup behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Pin lint-fix Cursor launches to use_config_context=False; replace configuration isolation/cleanup preserve language and tests with auth-export, startup-lock, run-external-agent capture, and wrapper-log cleanup that match current _run_cursor.
  - From Cursor-Innovation: Add an explicit plan step and test that lint-fix passes `use_config_context=False` and still runs the existing auth-export plus preflight path.
  - From Cursor-Pragmatic: Require `use_config_context=False` on lint-fix Cursor launches and align the plan language with auth-export parity. Drop "configuration isolation/cleanup" unless you can point at current behavior that actually does it.
  - From Cursor-Requirements: Pass use_config_context=False on every lint-fix Cursor run_vendor_launch call and add a parity test that no config-context temp dir is created


### [Plan Review] FINDING_3

### FINDING_3: Bound helper reuse to the established implement-lane sources
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Concern**: Unbounded reuse of private launcher execute helpers could couple the implement lint-fix lane to unrelated launcher modules and create future drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Name allowed sources (_run_external, _auth, launch-codex-exec-equivalent hooks already used by launch_codex_exec_main) and forbid implement imports of _drafter/_ci_launcher execute bodies; lane adapters stay in checks_lint_fix or shared _run_external helpers only.


### [Plan Review] FINDING_7

### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/agents/_vendor.py:270-283
- **Concern**: [SCOPE-REDUCTION] Reuse the existing Claude `workspace-write` profile instead of adding a lint-fix-specific Claude profile.. Scenario: `launch-claude-lint-fix` already uses `claude -p --output-format json --model <CLAUDE_CI_FIX_MODEL> --add-dir <repo> --allowedTools Read,Edit,Write`, which matches `workspace-write`; a new profile adds surface area with no argv delta.
- **Proposed resolution**: Plan Claude adoption as `CLAUDE_DESCRIPTOR`/`workspace-write` plus lane-owned lint-fix preamble/postprocess hooks only; skip a new Claude argv profile unless a byte diff is documented.


### [Plan Review] FINDING_8

### FINDING_8:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/agents/_vendor.py:677-682
- **Concern**: [SCOPE-REDUCTION] Pin use_config_context=false for lint-fix Cursor run_vendor_launch calls. Scenario: The plan says configuration isolation/cleanup but today's _run_cursor only runs cursor_auth_export_env and never enters cursor_config_context. run_vendor_launch defaults use_config_context to true for Cursor, which mkdtemp-copies cli-config and changes auth/preflight behavior versus the export-only path.
- **Proposed resolution**: Pass use_config_context=False on every lint-fix Cursor launch and replace configuration isolation/cleanup wording with auth-export parity. Do not enable cursor_config_context unless a measured behavior gap requires it.


---LARCH-REJECTED-END---
