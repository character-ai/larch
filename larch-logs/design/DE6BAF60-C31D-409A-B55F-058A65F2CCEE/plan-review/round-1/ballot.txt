### FINDING_1: Env-key dispatch-failure assertion can pass without argv capture
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The env-key dispatch-failure test checks that the sentinel is absent from argv capture, but the planned case never sets `TEST_AGENT_ARGV_FILE`, so the stub does not write argv and the grep can pass vacuously on a missing file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add TEST_AGENT_ARGV_FILE=<capture-path> to the new env-key dispatch-failure case env (mirror the codex-telemetry case at line 786) and grep that file for <REDACTED-TOKEN>

### FINDING_2: `/tmp` cleanup snapshot can abort on empty glob under `set -e`
- **Reviewer(s)**: Codex-Arch, Codex-dyn-harness-topology
- **Severity**: important
- **Concern**: The planned `/tmp/larch-codex-home-*` snapshot uses raw `ls -d` on a glob that may have no matches. In a `set -e` harness, a clean runner can abort before exercising the launcher cleanup behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Use a snapshot helper that guards empty matches, e.g. { ls -d /tmp/larch-codex-home-* 2>/dev/null || true; } | LC_ALL=C sort, then diff before vs after
  - From Codex-dyn-harness-topology: Specify a guarded snapshot helper, e.g. { ls -d /tmp/larch-codex-home-* 2>/dev/null || true; } | sort, or use find which exits 0 on no matches

### FINDING_3: Stub hook is aimed at a nonexistent standalone file
- **Reviewer(s)**: Cursor-Innovation, Cursor-dyn-harness-topology
- **Severity**: important
- **Concern**: The planned stub extension refers to a nonexistent `run-external-agent-stub.sh`, so the auth-link capture hook may be added nowhere and login-fallback assertions would never exercise the intended stub behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Document the heredoc at test-review-and-fix.sh:63-193 as the stub surface (same pattern as STUB_CODEX_AUTH_LINK_FILE in test-codex-implementer.sh:239-240)
  - From Cursor-dyn-harness-topology: Edit the heredoc stub created at lines 63-192 (same block as TEST_AGENT_CODEX_HOME_FILE / TEST_AGENT_CODEX_CONFIG_FILE), not a standalone run-external-agent-stub.sh file

### FINDING_4: Chmod restore ordering is internally inconsistent
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The plan contradicts itself on whether writable permissions are restored before or after assertions. If an assertion fails before restore, read-only fixture trees can remain and break scratch cleanup.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: A failed assertion between chmod a-w and restore can leave read-only fixture trees that break scratch trap rm -rf; align item 2 with t7a (restore before assertions)

### FINDING_5: Legacy env-key strip case would run in login-mode semantics
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The planned legacy env-key strip case omits `run_cr_with_env`; if it uses `run_cr`, `OPENAI_API_KEY` is unset and the case exercises login-mode stripping rather than env-key copy/strip behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Invoke the legacy strip case via run_cr_with_env (or a direct TMPDIR= wrapper like t10-env-key-false) with OPENAI_API_KEY set and HOME aimed at the fixture

### FINDING_6: Multiline fixture expansion may exceed the proven regression pin
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: latent
- **Concern**: The plan adds several multiline fixtures even though the audit only identified one proven false-green pin, risking extra coverage of awk edge cases already partially covered elsewhere.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Land the line-162/login-home pin first; add multiline fixtures only if issue #3476 gap 1 explicitly requires them

### FINDING_7: `env -u` cannot directly invoke a shell function
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Concern**: The plan specifies `env -u OPENAI_API_KEY run_review_and_fix`, but `run_review_and_fix` is a shell function, not an executable, so the harness would fail before testing dispatch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Use a function-safe unset in a subshell, e.g. ( unset OPENAI_API_KEY; HOME="$fixture_home" TEST_AGENT_BEHAVIOR=cursor-success TEST_AGENT_ARGV_FILE="$argv" run_review_and_fix ... ), then restore chmod immediately after the function returns.

### FINDING_8: New dispatch cases may use the developer HOME instead of fixture HOME
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The proposed review-and-fix dispatch cases depend on fixture `~/.codex` trees but do not export `HOME`, so auth/config operations may bind to the real user home, causing flakiness or false greens.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: New dispatch cases rely on fixture ~/.codex trees but never export HOME on run_review_and_fix run_review_and_fix inherits the developer HOME; review-and-fix copies/links via literal ~/.codex so fixture chmod/read-only and auth.json paths bind to the real user home — flaky or false-green on CI vs laptops Add HOME="$fixture_home" (absolute scratch path) to each new run_review_and_fix invocation; mirror test-codex-implementer.sh:381-393 / test-check-reviewers.sh:282

### FINDING_9: Probe-home cleanup assertion omits timeout branch
- **Reviewer(s)**: Codex-Requirements, Codex-dyn-auth-contract-drift
- **Severity**: important
- **Concern**: The planned probe temp `CODEX_HOME` cleanup coverage does not include the existing timeout path, so timeout cleanup could regress and leave copied config/auth material without failing tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add assert_no_probe_homes after the existing t-probe-to timeout case, or narrow the plan wording if timeout cleanup is intentionally out of scope.
  - From Codex-dyn-auth-contract-drift: Add assert_no_probe_homes after the existing t-probe-to case so the timeout branch is pinned too

### FINDING_10: Source-only `chmod a-w` may not force auth-prep failure
- **Reviewer(s)**: Cursor-dyn-auth-contract-drift
- **Severity**: important
- **Concern**: The plan assumes making fixture `HOME/.codex/config.toml` read-only will make copied temp config read-only, but plain `cp` into writable `mktemp` dirs normally creates writable destinations, so the intended login auth-prep failure may not occur.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-auth-contract-drift: For the new review-and-fix login auth-prep case (and any t7a hardening), copy one of those proven shims instead of relying on `cp` to preserve `a-w`; drop the inaccurate `cp preserves read-only` sentence from Approach

### FINDING_11: Trusted-project argv greps do not prove `-c` pairing
- **Reviewer(s)**: Codex-dyn-auth-contract-drift
- **Severity**: latent
- **Concern**: Separate greps for the project key and trusted value can pass even if the `-c` flag is dropped and the config string is passed as a bare argv element.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-auth-contract-drift: Assert an adjacent argv pair: a -c line immediately followed by the exact projects."<escaped repo>".trust_level="trusted" config string

### FINDING_12: Review-and-fix temp `CODEX_HOME` cleanup remains unpinned
- **Reviewer(s)**: Codex-dyn-auth-contract-drift
- **Severity**: important
- **Concern**: Existing review-and-fix telemetry captures the temp `CODEX_HOME` prefix but does not assert the temporary home is removed, so copied auth/config material could be left behind without test failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-auth-contract-drift: After a dispatch case that captures TEST_AGENT_CODEX_HOME_FILE, assert the captured larch-codex-review-fix-home.* path no longer exists
