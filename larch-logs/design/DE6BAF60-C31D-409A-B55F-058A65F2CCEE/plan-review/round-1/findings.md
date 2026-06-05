### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/test-review-and-fix.sh:59-62
- **Concern**: Env-key dispatch-failure case asserts sentinel absent from argv capture but never sets TEST_AGENT_ARGV_FILE. Scenario: Stub only writes argv when TEST_AGENT_ARGV_FILE is set (lines 82-83); without it the sentinel-absent grep on a missing file exits 0 and the assertion passes vacuously — same false-green class the plan warns about at Failure modes #1
- **Proposed resolution**: Add TEST_AGENT_ARGV_FILE=<capture-path> to the new env-key dispatch-failure case env (mirror the codex-telemetry case at line 786) and grep that file for <REDACTED-TOKEN>

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/test-codex-implementer.sh:312-334,455-474
- **Concern**: Planned /tmp snapshot uses ls -d on a glob that commonly has no matches under set -e. Scenario: Clean machines with no /tmp/larch-codex-home-* entries abort before the launcher run, so the new cleanup assertion never tests the target behavior
- **Proposed resolution**: Use a snapshot helper that guards empty matches, e.g. { ls -d /tmp/larch-codex-home-* 2>/dev/null || true; } | LC_ALL=C sort, then diff before vs after

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/review-and-fix/scripts/test-review-and-fix.sh:63-193
- **Concern**: Stub extension targets a non-existent standalone run-external-agent-stub.sh. Scenario: Implementer edits a missing file or skips the TEST_AGENT_CODEX_AUTH_LINK_FILE hook; login-fallback assertions never run
- **Proposed resolution**: Document the heredoc at test-review-and-fix.sh:63-193 as the stub surface (same pattern as STUB_CODEX_AUTH_LINK_FILE in test-codex-implementer.sh:239-240)

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:50-54 vs plan.txt:84-94
- **Concern**: chmod u+w restore order contradicts itself. Scenario: Item 2 lists restore after assertions; Edge cases/Failure modes #3 require restore immediately after run_review_and_fix and before assertions
- **Proposed resolution**: A failed assertion between chmod a-w and restore can leave read-only fixture trees that break scratch trap rm -rf; align item 2 with t7a (restore before assertions)

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-check-reviewers.sh:28-40
- **Concern**: Legacy env-key strip case omits run_cr_with_env. Scenario: run_cr always runs env -u OPENAI_API_KEY; a case that follows run_cr will exercise login-mode strip semantics instead of env-key copy/strip
- **Proposed resolution**: Invoke the legacy strip case via run_cr_with_env (or a direct TMPDIR= wrapper like t10-env-key-false) with OPENAI_API_KEY set and HOME aimed at the fixture

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: plan.txt:23-26
- **Concern**: Three new multiline fixtures beyond the one proven false-green pin. Scenario: Audit classified only line 162 as DEFECTIVE; ~100+ added lines test awk corners already partially covered at strip-edge-config.toml:146-155
- **Proposed resolution**: Land the line-162/login-home pin first; add multiline fixtures only if issue #3476 gap 1 explicitly requires them

### FINDING_7:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/test-review-and-fix.sh:308-318
- **Concern**: The plan specifies env -u OPENAI_API_KEY for new run_review_and_fix cases, but run_review_and_fix is a shell function, not an executable.. Scenario: If implemented as env -u OPENAI_API_KEY run_review_and_fix ..., the harness searches PATH for run_review_and_fix and fails before testing dispatch.
- **Proposed resolution**: Use a function-safe unset in a subshell, e.g. ( unset OPENAI_API_KEY; HOME="$fixture_home" TEST_AGENT_BEHAVIOR=cursor-success TEST_AGENT_ARGV_FILE="$argv" run_review_and_fix ... ), then restore chmod immediately after the function returns.

### FINDING_8:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/test-review-and-fix.sh:308-318
- **Concern**: skills/review-and-fix/scripts/review-and-fix.sh:280-281. Scenario: skills/review-and-fix/scripts/test-review-and-fix.sh (proposed auth-prep and login-fallback cases)
- **Proposed resolution**: New dispatch cases rely on fixture ~/.codex trees but never export HOME on run_review_and_fix run_review_and_fix inherits the developer HOME; review-and-fix copies/links via literal ~/.codex so fixture chmod/read-only and auth.json paths bind to the real user home — flaky or false-green on CI vs laptops Add HOME="$fixture_home" (absolute scratch path) to each new run_review_and_fix invocation; mirror test-codex-implementer.sh:381-393 / test-check-reviewers.sh:282

### FINDING_9:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: latent
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:32-36; scripts/test-check-reviewers.sh:465-485
- **Concern**: Plan says probe temp CODEX_HOME cleanup is covered on all exit paths, but omits the existing timeout path from the planned cleanup assertions. Scenario: A Codex probe timeout could regress to leaving larch-codex-probe-home.* behind with copied config/auth material without failing the harness
- **Proposed resolution**: Add assert_no_probe_homes after the existing t-probe-to timeout case, or narrow the plan wording if timeout cleanup is intentionally out of scope.

### FINDING_10:
- **Reviewer(s)**: Cursor-dyn-auth-contract-drift
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:77-78, scripts/check-reviewers.sh:211-212, skills/review-and-fix/scripts/review-and-fix.sh:280-281
- **Concern**: Approach claims chmod a-w on fixture `HOME/.codex/config.toml` plus plain `cp` forces login auth-prep failure because the destination stays read-only. Scenario: `external_strip_codex_larch_env_provider` only fails its `-w` precheck when the temp target is non-writable (`scripts/lib-external-launcher-common.sh:539`); both call sites use writable `mktemp` dirs and plain `cp`, which normally creates a writable destination. Repo precedents that actually force failure use a `mktemp` shim that chmods the created home config (`scripts/test-launch-codex-ci.sh:126-138`) or a PATH `mv` shim (`skills/implement/scripts/test-codex-implementer.sh:445-449`), not source-only chmod
- **Proposed resolution**: For the new review-and-fix login auth-prep case (and any t7a hardening), copy one of those proven shims instead of relying on `cp` to preserve `a-w`; drop the inaccurate `cp preserves read-only` sentence from Approach

### FINDING_11:
- **Reviewer(s)**: Codex-dyn-auth-contract-drift
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-check-reviewers.sh:465-485
- **Concern**: FINDING_1: The proposed probe-home cleanup helper skips the existing timeout probe path. Scenario: check-reviewers.sh creates CODEX_HOME before polling and also cleans it after timeout at scripts/check-reviewers.sh:253-269; if that timeout cleanup regresses, the proposed t6/t7/t9/t7a checks still pass
- **Proposed resolution**: Add assert_no_probe_homes after the existing t-probe-to case so the timeout branch is pinned too

### FINDING_12:
- **Reviewer(s)**: Codex-dyn-auth-contract-drift
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/test-check-reviewers.sh:377-401
- **Concern**: FINDING_2: The proposed trusted-project argv greps do not prove the value is passed via -c. Scenario: Grepping separately for projects. and trust_level="trusted" would still pass if the -c flag were dropped and the config string survived as a bare argv element
- **Proposed resolution**: Assert an adjacent argv pair: a -c line immediately followed by the exact projects."<escaped repo>".trust_level="trusted" config string

### FINDING_13:
- **Reviewer(s)**: Codex-dyn-auth-contract-drift
- **Severity**: important
- **Focus area**: security
- **Location**: skills/review-and-fix/scripts/test-review-and-fix.sh:773-816
- **Concern**: FINDING_3: review-and-fix temp CODEX_HOME cleanup remains unpinned. Scenario: The existing telemetry fixture captures the temp CODEX_HOME but only checks its prefix; removing the explicit rm at skills/review-and-fix/scripts/review-and-fix.sh:332 would leave copied auth/config material behind while the proposed tests still pass
- **Proposed resolution**: After a dispatch case that captures TEST_AGENT_CODEX_HOME_FILE, assert the captured larch-codex-review-fix-home.* path no longer exists

### FINDING_14:
- **Reviewer(s)**: Cursor-dyn-harness-topology
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/test-review-and-fix.sh:63-192
- **Concern**: Stub extension targets nonexistent run-external-agent-stub.sh. Scenario: TEST_AGENT_CODEX_AUTH_LINK_FILE would be added to a repo path that does not exist; dispatch shard never gains the capture hook
- **Proposed resolution**: Edit the heredoc stub created at lines 63-192 (same block as TEST_AGENT_CODEX_HOME_FILE / TEST_AGENT_CODEX_CONFIG_FILE), not a standalone run-external-agent-stub.sh file

### FINDING_15:
- **Reviewer(s)**: Codex-dyn-harness-topology
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/test-codex-implementer.sh:8; <TMPDIR>/plan.txt:68-70
- **Concern**: Planned /tmp snapshot uses raw ls under a set -e harness. Scenario: A clean runner with no /tmp/larch-codex-home-* makes ls return nonzero before the launcher runs, so the new cleanup test can abort instead of asserting leaks
- **Proposed resolution**: Specify a guarded snapshot helper, e.g. { ls -d /tmp/larch-codex-home-* 2>/dev/null || true; } | sort, or use find which exits 0 on no matches
