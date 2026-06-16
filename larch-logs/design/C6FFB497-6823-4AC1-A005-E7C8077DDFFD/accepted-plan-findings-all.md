### FINDING_1: _debug-step5c.sh fake CLI rejects validate-design-tmpdir
- **Reviewer(s)**: Codex-Arch, Codex-Pragmatic, Cursor-dyn-retirement-completeness, Codex-dyn-retirement-completeness
- **Severity**: blocking
- **Concern**: `skills/design/scripts/_debug-step5c.sh` uses a minimal inline `FAKE/python/cli.py` stub that exits 2 for unknown verbs, not a symlinked real `python/` tree. After `design-stage-terminal-state.sh` is repointed to call `python3 "$PLUGIN_ROOT/python/cli.py" session validate-design-tmpdir`, the Step 5c debug path aborts before terminal-state staging runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add a session validate-design-tmpdir branch that exits 0, or replace the fake-only cli.py setup with a real python/ directory symlink like the other Step 5c debug harness
  - From Codex-Pragmatic: Add a session validate-design-tmpdir exit-0 branch to the fake cli.py, matching scripts/debug-step5c-once.sh
  - From Cursor-dyn-retirement-completeness: Add ### UPDATED: skills/design/scripts/_debug-step5c.sh: remove lib symlink (line 12) and extend the inline cli.py stub (line 15) with if len(sys.argv) >= 3 and sys.argv[1] == "session" and sys.argv[2] == "validate-design-tmpdir": raise SystemExit(0) before the final raise SystemExit(2); also add stall-recovery validate-token and validate-terminal-state exit-0 branches if full terminal-state staging should succeed
  - From Codex-dyn-retirement-completeness: Add the same session validate-design-tmpdir exit-0 branch to the _debug-step5c.sh fake cli.py, or replace that stub with a real cli.py passthrough


### FINDING_2: Validator initializes quiet logging before tmpdir allowlist check
- **Reviewer(s)**: Codex-Innovation, Codex-Pragmatic, Codex-Requirements
- **Severity**: blocking
- **Concern**: `validate_design_tmpdir_main` calls `logging_util.quiet_init` before validating the candidate `DESIGN_TMPDIR`. When wrappers export `DESIGN_TMPDIR` to an existing disallowed or symlinked directory, quiet logging can create a `larch-quiet-*.log` there before the allowlist check rejects the path, regressing the validator's no-write-before-allowlist contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Remove logging_util.quiet_init from validate_design_tmpdir_main and print validation failures directly to stderr with _plain_err or print.
  - From Codex-Pragmatic: Do not call quiet_init in this validator; emit failures directly to stderr with _plain_err or equivalent after validate_design_tmpdir returns
  - From Codex-Requirements: Validate first and write failures directly to stderr without quiet_init; only initialize quiet logging after a successful validation if needed


### FINDING_3: test-design-step3-review.sh fake CLI missing validate-design-tmpdir branch
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: The plan does not update the fake CLI stub in `skills/design/scripts/test-design-step3-review.sh`. In the kill-helper test, `design-step3-review.sh` will call `session validate-design-tmpdir` against the fake CLI, hit the generic `HELPER_RC=73` path, and exit before the loop assertions run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add an explicit session validate-design-tmpdir exit-0 or real-CLI delegation branch before the helper logging fallback in that stub


### FINDING_4:
- **Reviewer(s)**: Codex-dyn-retirement-completeness
- **Severity**: important
- **Focus area**: security
- **Location**: <TMPDIR>/plan.txt:27-40; python/logging_util.py:45-83; SECURITY.md:166
- **Concern**: [SCOPE-REDUCTION] validate_design_tmpdir_main initializes quiet logging before validating the candidate path. Scenario: A wrapper with exported DESIGN_TMPDIR set to a disallowed existing directory can make quiet_init create larch-quiet-design-tmpdir-validate-<pid>.log under that directory before the validator rejects it, violating the no-write-before-allowlist contract
- **Proposed resolution**: Remove quiet_init from this validator-only verb, or move it after validation; emit failures directly to stderr without creating a quiet log


### FINDING_5:
- **Reviewer(s)**: Codex-dyn-verb-wiring
- **Severity**: important
- **Focus area**: security
- **Location**: <TMPDIR>/plan.txt:25-40; python/logging_util.py:64-83; skills/design/scripts/design-step3-entry.sh:21-30
- **Concern**: [SCOPE-REDUCTION] validate_design_tmpdir_main initializes quiet logging before validation. Scenario: `logging_util.quiet_init` chooses `DESIGN_TMPDIR` and creates a quiet log before `validate_design_tmpdir` runs. A caller with an exported, existing, disallowed `DESIGN_TMPDIR` can write `larch-quiet-design-tmpdir-validate-*.log` outside the allowlist before the new validator rejects it.
- **Proposed resolution**: Remove `logging_util.quiet_init` from this stderr-only verb, or move any quiet setup after successful validation. On failure, write the existing validator message directly to stderr, for example with `_plain_err(message)`, while still returning 2.




### FINDING_1:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: security
- **Location**: skills/design/scripts/design-step3-mav.sh:83-94; skills/design/scripts/design-stage-terminal-state.sh:9-56; skills/design/scripts/design-failure-report.sh:9-43
- **Concern**: Quiet wrappers validate through the new child CLI only after larch_quiet_init. Scenario: For a rejected DESIGN_TMPDIR, these wrappers already have stderr redirected to a quiet log. The proposed child CLI message goes into that log instead of caller stderr, unlike the sourced bash validator which used larch_err. It can also create larch-quiet-*.log under a disallowed existing DESIGN_TMPDIR before rejection.
- **Proposed resolution**: Source lib-quiet if needed, but defer larch_quiet_init until after successful validate-design-tmpdir in these wrappers, or otherwise validate before quiet log selection.


