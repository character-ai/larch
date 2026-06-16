### FINDING_1:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/_debug-step5c.sh:14-15
- **Concern**: Fake CLI still exits 2 for session validate-design-tmpdir. Scenario: The plan removes the lib symlink here, but this harness writes a fake python/cli.py whose fallback raises SystemExit(2); after design-stage-terminal-state.sh is repointed, the Step 5c debug path aborts before staging terminal state
- **Proposed resolution**: Add a session validate-design-tmpdir branch that exits 0, or replace the fake-only cli.py setup with a real python/ directory symlink like the other Step 5c debug harness

### FINDING_1:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: security
- **Location**: python/session_env.py:558; python/logging_util.py:49-78
- **Concern**: Proposed validator CLI initializes quiet logging before validation. Scenario: Wrappers source an exported DESIGN_TMPDIR before calling the new verb. logging_util.quiet_init can create a larch-quiet log under that unvalidated directory before validate_design_tmpdir rejects it, so an invalid existing design tmpdir gets written to before the security gate runs.
- **Proposed resolution**: Remove logging_util.quiet_init from validate_design_tmpdir_main and print validation failures directly to stderr with _plain_err or print.

### FINDING_1:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: blocking
- **Focus area**: security
- **Location**: python/session_env.py:522-558; python/logging_util.py:64-82
- **Concern**: validate_design_tmpdir_main initializes quiet logging before validating the candidate. Scenario: With DESIGN_TMPDIR set to an existing disallowed or symlinked directory, quiet_init can create larch-quiet-design-tmpdir-validate-*.log there before the allowlist check rejects the path
- **Proposed resolution**: Do not call quiet_init in this validator; emit failures directly to stderr with _plain_err or equivalent after validate_design_tmpdir returns

### FINDING_2:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/_debug-step5c.sh:14-15
- **Concern**: The plan says _debug-step5c already symlinks python, but it only writes a minimal fake cli.py that exits 2 for unknown verbs. Scenario: After design-stage-terminal-state switches to session validate-design-tmpdir, this debug helper fails before staging terminal state
- **Proposed resolution**: Add a session validate-design-tmpdir exit-0 branch to the fake cli.py, matching scripts/debug-step5c-once.sh

### FINDING_1:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: security
- **Location**: python/session_env.py:558
- **Concern**: CLI validator initializes quiet logging before validating the candidate tmpdir. Scenario: If DESIGN_TMPDIR names an existing disallowed directory, validate_design_tmpdir_main can create a quiet log there before rejecting it, regressing the validator's no-write-before-allowlist contract
- **Proposed resolution**: Validate first and write failures directly to stderr without quiet_init; only initialize quiet logging after a successful validation if needed

### FINDING_2:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/test-design-step3-review.sh:159-179
- **Concern**: The plan misses the fake CLI branch needed for the new validation verb. Scenario: In the kill-helper test, design-step3-review.sh will call session validate-design-tmpdir against the fake CLI, hit the generic HELPER_RC=73 path, and exit before the loop assertions
- **Proposed resolution**: Add an explicit session validate-design-tmpdir exit-0 or real-CLI delegation branch before the helper logging fallback in that stub

### FINDING_1:
- **Reviewer(s)**: Cursor-dyn-retirement-completeness
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: skills/design/scripts/_debug-step5c.sh:12-15
- **Concern**: _debug-step5c.sh uses an inline minimal FAKE/python/cli.py stub (lines 14-15), not a symlinked python/ tree; plan only removes the lib symlink and falsely claims the whole python/ dir is already symlinked (line 10 is design-stage-terminal-state.sh). Scenario: After design-stage-terminal-state.sh is repointed to python3 "$PLUGIN_ROOT/python/cli.py" session validate-design-tmpdir, the stub exits 2 before publish-tail terminal-state staging runs; manual debug of Step 5c publish failure breaks
- **Proposed resolution**: Add ### UPDATED: skills/design/scripts/_debug-step5c.sh: remove lib symlink (line 12) and extend the inline cli.py stub (line 15) with if len(sys.argv) >= 3 and sys.argv[1] == "session" and sys.argv[2] == "validate-design-tmpdir": raise SystemExit(0) before the final raise SystemExit(2); also add stall-recovery validate-token and validate-terminal-state exit-0 branches if full terminal-state staging should succeed

### FINDING_1:
- **Reviewer(s)**: Codex-dyn-retirement-completeness
- **Severity**: important
- **Focus area**: security
- **Location**: <TMPDIR>/plan.txt:27-40; python/logging_util.py:45-83; SECURITY.md:166
- **Concern**: [SCOPE-REDUCTION] validate_design_tmpdir_main initializes quiet logging before validating the candidate path. Scenario: A wrapper with exported DESIGN_TMPDIR set to a disallowed existing directory can make quiet_init create larch-quiet-design-tmpdir-validate-<pid>.log under that directory before the validator rejects it, violating the no-write-before-allowlist contract
- **Proposed resolution**: Remove quiet_init from this validator-only verb, or move it after validation; emit failures directly to stderr without creating a quiet log

### FINDING_2:
- **Reviewer(s)**: Codex-dyn-retirement-completeness
- **Severity**: latent
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:104-108; <TMPDIR>/plan.txt:160; skills/design/scripts/_debug-step5c.sh:14-16
- **Concern**: _debug-step5c is misclassified as using a real cli.py, so its stub will reject the new validate verb. Scenario: After design-stage-terminal-state.sh switches to python/cli.py session validate-design-tmpdir, the fake cli.py in _debug-step5c.sh exits 2 for that verb and the debug helper no longer reaches terminal-state staging
- **Proposed resolution**: Add the same session validate-design-tmpdir exit-0 branch to the _debug-step5c.sh fake cli.py, or replace that stub with a real cli.py passthrough

### FINDING_1:
- **Reviewer(s)**: Codex-dyn-verb-wiring
- **Severity**: important
- **Focus area**: security
- **Location**: <TMPDIR>/plan.txt:25-40; python/logging_util.py:64-83; skills/design/scripts/design-step3-entry.sh:21-30
- **Concern**: [SCOPE-REDUCTION] validate_design_tmpdir_main initializes quiet logging before validation. Scenario: `logging_util.quiet_init` chooses `DESIGN_TMPDIR` and creates a quiet log before `validate_design_tmpdir` runs. A caller with an exported, existing, disallowed `DESIGN_TMPDIR` can write `larch-quiet-design-tmpdir-validate-*.log` outside the allowlist before the new validator rejects it.
- **Proposed resolution**: Remove `logging_util.quiet_init` from this stderr-only verb, or move any quiet setup after successful validation. On failure, write the existing validator message directly to stderr, for example with `_plain_err(message)`, while still returning 2.

