### FINDING_1:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: security
- **Location**: python/larch/state/session_env.py:390-405
- **Concern**: The proposed helper still trusts an attacker-selected directory that merely has a canonical-looking session name. Scenario: The checker accepts an attacker-created `<TMPDIR>` directory. A direct caller can place matching authorization and run-ID values there, pass that directory as `--trusted-root`, and reach `gh`, so the issue's authorization bypass remains
- **Proposed resolution**: Add a minimal check that proves the trusted root belongs to a live guarded session rather than relying only on its parent and basename, then cover the forged canonical-directory case in the planned negative tests



### FINDING_2:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: security
- **Location**: scripts/file-failure-report-cross-repo.sh:16-32
- **Concern**: Caller-provided trusted root remains forgeable by a direct helper caller. Scenario: A caller can create an allowed-path directory named claude-design-* or claude-implement-*, place a valid-looking context file inside it, choose a matching run ID, and pass all three arguments. The unchanged Python checker accepts the directory shape without proving that it belongs to a live guarded run, so the plan does not close the issue's direct-caller authorization bypass.
- **Proposed resolution**: Bind authorization to independently established live-session state rather than trusting all caller-supplied values. For example, resolve the trusted root and run identity from a live-run registry or remove direct mutation authority from the shell helper and expose it only through an already-authorized Python caller.



