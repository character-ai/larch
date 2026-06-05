### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-check-reviewers.sh:330-349
- **Concern**: Plan items 3–4 attach trusted-project argv and sentinel-leak checks to t10 login-stamp case. Scenario: t10 uses a fresh login true stamp so codex is never invoked; argv capture stays empty and OPENAI_API_KEY is unset, so sentinel grep passes vacuously and cannot catch regressions
- **Proposed resolution**: Target t10-env-key-false (or another live env-key probe case that sets OPENAI_API_KEY and LARCH_TEST_CODEX_ARGV_LOG); only assert argv/trusted-project/sentinel after a probe that actually runs codex

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch, Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/test-review-and-fix.sh:47-51
- **Concern**: Login-fallback case omits clearing OPENAI_API_KEY. Scenario: A parent/CI OPENAI_API_KEY forces the env-key branch; symlink/auth-link and CODER_TOOL=codex assertions would validate the wrong path
- **Proposed resolution**: Wrap the case in a subshell with unset OPENAI_API_KEY (same pattern as the auth-prep-failure case) and assert env-key argv overrides are absent

### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/test-review-and-fix.sh:42-46
- **Concern**: Auth-prep-failure case relies on read-only fixture .codex/config.toml. Scenario: review-and-fix copies ~/.codex/config.toml into a writable temp CODEX_HOME before external_prepare_codex_auth (review-and-fix.sh:280-285); read-only source does not fail prep, so codex may still run and the planned auth-setup/argv-absent assertions can false-green
- **Proposed resolution**: Mirror test-codex-implementer.sh 4h: force strip/prep failure via a PATH mv stub (or equivalent) while keeping chmod restore after the run; drop read-only config as the sole failure trigger

### FINDING_4:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-check-reviewers.sh:330-349
- **Concern**: Plan pins trusted-project argv checks on t10 stamp-hit case. Scenario: t10 cache hit skips Codex invocation so no argv is logged and trusted-project -c assertions cannot run
- **Proposed resolution**: Use a live-probe case such as t10-env-key-false t6 or expired-stamp t11 for trust_level and projects argv capture

### FINDING_5:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-lib-external-launcher-common.sh:135-166
- **Concern**: Exactly-one grep -Fxc conflicts with new multiline fixtures. Scenario: Adding verbatim model_provider lines inside multiline bodies pushes grep -Fxc above 1 and fails the new harness
- **Proposed resolution**: Split fixtures per scenario scope the count assertion or replace -Fxc == 1 with targeted assertions only

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-check-reviewers.sh:27-30
- **Concern**: LARCH_TEST_CODEX_CONFIG_CAPTURE is not wired anywhere. Scenario: Plan item 5 requires capturing probe temp config via LARCH_TEST_CODEX_CONFIG_CAPTURE but no script reads that variable and Approach forbids production changes; implementer cannot assert stripped temp config without a new seam or a different capture strategy
- **Proposed resolution**: Use existing argv logging plus before/after fixture checksum only or call external_prepare_codex_auth in test-lib-external-launcher-common.sh; if probe-path strip must be locked drop the capture requirement or add an explicit one-line test seam to check-reviewers.sh and allow that production touch

### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-check-reviewers.sh:330-401
- **Concern**: t10 label mismatches env-key argv and sentinel work. Scenario: Items 3-4 anchor trusted-project -c and <REDACTED-TOKEN> absence to t10 but t10 is login-stamp cache hit with no OPENAI_API_KEY and no codex invocation; sentinel grep would be vacuous against plan Edge cases
- **Proposed resolution**: Rename targets to t10-env-key-false (live probe with OPENAI_API_KEY and LARCH_TEST_CODEX_ARGV_LOG) for trust_level/projects assertions and recursive TMPDIR sentinel scan

### FINDING_8:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/test-review-and-fix.sh:308-319
- **Concern**: Login auth-prep failure fixture is too weak. Scenario: Read-only HOME/.codex/config.toml does not make external_prepare_codex_auth fail because review-and-fix.sh copies into a writable temp CODEX_HOME before strip/symlink; case can pass with codex dispatch and miss auth-setup failure assertions
- **Proposed resolution**: Mirror skills/implement/scripts/test-codex-implementer.sh:441-449 mv-stub on PATH or make the temp CODEX_HOME unwritable; keep unset OPENAI_API_KEY subshell and chmod restore after return

### FINDING_9:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:33-34
- **Concern**: Plan items 3-4 label the trust/sentinel targets as t10 / t10 env-key argv capture, but only t10-env-key-false runs a live probe with OPENAI_API_KEY=<REDACTED-TOKEN> and an argv log; t10 is a login-stamp cache hit (no codex) and t10-env-key is an env-key stamp cache hit (no codex). Scenario: Literal wiring adds vacuous always-pass trust argv and sentinel greps on non-invocation cases and may skip the live env-key probe path the assertions are meant to lock
- **Proposed resolution**: Name the live-probe case explicitly (t10-env-key-false): assert trust_level/projects. -c entries in its argv log and recursively grep that case TMPDIR for <REDACTED-TOKEN> absence

### FINDING_10:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-lib-external-launcher-common.sh:135-166
- **Concern**: Plan combines an exact one-line retained selector count with a new verbatim multiline selector fixture. Scenario: If the new ''' multiline fixture contains an exact model_provider = "openai-larch-env" line, strip-edge-config.toml will retain both the existing multiline selector and the new one, so the proposed grep -Fxc == 1 assertion fails
- **Proposed resolution**: Keep the exact-count assertion scoped to the existing fixture, put the new multiline fixture in a separate temp config, or update the expected count to match the added exact retained selector lines

### FINDING_11:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-check-reviewers.sh:346-349
- **Concern**: Plan items 3-4 target t10 login stamp cache hit. Scenario: t10 never invokes codex and never sets OPENAI_API_KEY so trusted-project argv and <REDACTED-TOKEN> absence checks are vacuous or never run
- **Proposed resolution**: Retarget items 3-4 to t10-env-key-false (live env-key probe with LARCH_TEST_CODEX_ARGV_LOG) or t6m; keep t10 as login-only stamp coverage

### FINDING_12:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/test-check-reviewers.sh:377-401
- **Concern**: Trusted-project argv assertion does not prove -c pairing. Scenario: The test could pass if projects."...".trust_level="trusted" is present as a bare argv item after the -c flag is accidentally dropped
- **Proposed resolution**: Assert an adjacent argv pair: a -c line followed by the exact trusted-project config string

### FINDING_13:
- **Reviewer(s)**: Cursor-dyn-harness-oracles
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-check-reviewers.sh:330-349
- **Concern**: Plan pins sentinel-absence grep to t10 login stamp hit. Scenario: t10 uses run_cr which unsets OPENAI_API_KEY and a fresh login true stamp with LARCH_PROBE_TTL_SECONDS=3600 so check-reviewers never runs larch_run_one_codex_probe; recursive grep for <REDACTED-TOKEN> passes even if live-probe logging regresses
- **Proposed resolution**: Move sentinel-absence grep to a live env-key probe case (e.g. t10-env-key-false after argv capture) or any t* run with OPENAI_API_KEY=<REDACTED-TOKEN> and a false/missing env-key stamp

### FINDING_14:
- **Reviewer(s)**: Codex-dyn-harness-oracles
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-lib-external-launcher-common.sh:135-166
- **Concern**: Planned exact-count selector oracle is ambiguous. Scenario: The fixture has both a nested table selector and an intended multiline selector, so a bug that strips the multiline body but leaves one table-scoped selector can still satisfy “exactly one retained model_provider”
- **Proposed resolution**: Add one scoped assertion that the retained selector is in the multiline body, or explicitly assert the nested `[model_providers.other]` selector line is absent in addition to the count.

### FINDING_15:
- **Reviewer(s)**: Codex-dyn-auth-state-contracts
- **Severity**: important
- **Focus area**: architecture
- **Location**: scripts/test-check-reviewers.sh:354-356; scripts/check-reviewers.sh:211-214; <TMPDIR>/plan.txt:27-31
- **Concern**: Plan relies on LARCH_TEST_CODEX_CONFIG_CAPTURE, but no current check-reviewers contract reads that env var; existing test stubs only capture argv.. Scenario: Following the plan literally either adds a shipped test hook to scripts/check-reviewers.sh, breaking the tests-only minimum-change contract, or leaves the legacy env_key strip case unable to inspect the private CODEX_HOME before cleanup.
- **Proposed resolution**: Keep capture test-local: in that case’s codex PATH stub, copy "$CODEX_HOME/config.toml" to "$LARCH_TEST_CODEX_CONFIG_CAPTURE" when both are set, then assert on the copied file without changing production scripts.

### OOS_1:
- **Description**: Legacy env-key strip case overlaps lib harness. Scenario: test-lib-external-launcher-common.sh already exercises strip/retain contracts on copied configs; probe-path case adds ~30+ lines and a new capture env unless trimmed
- **Reviewer**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: architecture
- **Location**: scripts/test-check-reviewers.sh:27-401
- **Phase**: design

### OOS_2:
- **Description**: /tmp snapshot helper duplicates STUB_CODEX_HOME_FILE. Scenario: Happy path already records CODEX_HOME via STUB_CODEX_HOME_FILE; before/after ls snapshot adds harness surface for the same invariant
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/implement/scripts/test-codex-implementer.sh:312-353
- **Phase**: design
