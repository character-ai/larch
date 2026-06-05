### FINDING_1: t10 stamp-hit target makes argv and sentinel assertions vacuous
- **Reviewer(s)**: Cursor-Arch, Cursor-Edge, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-harness-oracles
- **Severity**: important
- **Concern**: Plan items 3–4 attach trusted-project argv and sentinel-leak assertions to t10/t10 env-key stamp-hit cases that do not invoke Codex and may not set OPENAI_API_KEY. The assertions can therefore pass without exercising the live env-key probe path they are meant to validate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Target t10-env-key-false (or another live env-key probe case that sets OPENAI_API_KEY and LARCH_TEST_CODEX_ARGV_LOG); only assert argv/trusted-project/sentinel after a probe that actually runs codex
  - From Cursor-Edge: Use a live-probe case such as t10-env-key-false t6 or expired-stamp t11 for trust_level and projects argv capture
  - From Cursor-Innovation: Rename targets to t10-env-key-false (live probe with OPENAI_API_KEY and LARCH_TEST_CODEX_ARGV_LOG) for trust_level/projects assertions and recursive TMPDIR sentinel scan
  - From Cursor-Pragmatic: Name the live-probe case explicitly (t10-env-key-false): assert trust_level/projects. -c entries in its argv log and recursively grep that case TMPDIR for <REDACTED-TOKEN> absence
  - From Cursor-Requirements: Retarget items 3-4 to t10-env-key-false (live env-key probe with LARCH_TEST_CODEX_ARGV_LOG) or t6m; keep t10 as login-only stamp coverage
  - From Cursor-dyn-harness-oracles: Move sentinel-absence grep to a live env-key probe case (e.g. t10-env-key-false after argv capture) or any t* run with OPENAI_API_KEY=<REDACTED-TOKEN> and a false/missing env-key stamp

### FINDING_2: login-fallback test can accidentally take env-key branch
- **Reviewer(s)**: Cursor-Arch, Cursor-Edge
- **Severity**: important
- **Concern**: The login-fallback case does not clear OPENAI_API_KEY, so a parent or CI environment key can force the env-key branch and make symlink/auth-link plus CODER_TOOL=codex assertions validate the wrong path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Wrap the case in a subshell with unset OPENAI_API_KEY (same pattern as the auth-prep-failure case) and assert env-key argv overrides are absent

### FINDING_3: auth-prep failure fixture does not actually force prep failure
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: important
- **Concern**: The auth-prep-failure test relies on a read-only source config, but review-and-fix copies that config into a writable temp CODEX_HOME before auth preparation. Codex may still run, causing auth-setup/argv-absent assertions to false-green.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Mirror test-codex-implementer.sh 4h: force strip/prep failure via a PATH mv stub (or equivalent) while keeping chmod restore after the run; drop read-only config as the sole failure trigger
  - From Cursor-Innovation: Mirror skills/implement/scripts/test-codex-implementer.sh:441-449 mv-stub on PATH or make the temp CODEX_HOME unwritable; keep unset OPENAI_API_KEY subshell and chmod restore after return

### FINDING_4: exact-count selector oracle is unreliable for multiline fixtures
- **Reviewer(s)**: Cursor-Edge, Codex-Pragmatic, Codex-dyn-harness-oracles
- **Severity**: important
- **Concern**: The planned grep -Fxc == 1 selector assertion conflicts with or becomes ambiguous under multiline/nested selector fixtures. It can fail when multiple valid retained selector lines exist, or pass even if the intended multiline body is stripped while another selector remains.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Split fixtures per scenario scope the count assertion or replace -Fxc == 1 with targeted assertions only
  - From Codex-Pragmatic: Keep the exact-count assertion scoped to the existing fixture, put the new multiline fixture in a separate temp config, or update the expected count to match the added exact retained selector lines
  - From Codex-dyn-harness-oracles: Add one scoped assertion that the retained selector is in the multiline body, or explicitly assert the nested `[model_providers.other]` selector line is absent in addition to the count.

### FINDING_5: LARCH_TEST_CODEX_CONFIG_CAPTURE is not currently wired
- **Reviewer(s)**: Cursor-Innovation, Codex-dyn-auth-state-contracts
- **Severity**: important
- **Concern**: The plan depends on LARCH_TEST_CODEX_CONFIG_CAPTURE to inspect the probe temp config, but current scripts do not read that variable. Implementing literally either leaves the assertion impossible or requires adding a shipped test hook contrary to the stated tests-only/minimum-change approach.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Use existing argv logging plus before/after fixture checksum only or call external_prepare_codex_auth in test-lib-external-launcher-common.sh; if probe-path strip must be locked drop the capture requirement or add an explicit one-line test seam to check-reviewers.sh and allow that production touch
  - From Codex-dyn-auth-state-contracts: Keep capture test-local: in that case’s codex PATH stub, copy "$CODEX_HOME/config.toml" to "$LARCH_TEST_CODEX_CONFIG_CAPTURE" when both are set, then assert on the copied file without changing production scripts.

### FINDING_6: trusted-project argv assertion does not prove adjacent -c pairing
- **Reviewer(s)**: Codex-Requirements
- **Severity**: latent
- **Concern**: The trusted-project argv assertion could pass if the trusted config string appears as a bare argv item after the -c flag is accidentally dropped.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Assert an adjacent argv pair: a -c line followed by the exact trusted-project config string
