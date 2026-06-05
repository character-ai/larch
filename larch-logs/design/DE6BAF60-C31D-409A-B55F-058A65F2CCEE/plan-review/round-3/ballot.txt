### FINDING_1: Missing env-key auth-prep failure harness
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The plan does not test the OPENAI_API_KEY/env-key auth-prep failure path where Codex auth setup fails before Cursor fallback, so regressions that drop the env-key breadcrumb or sidecar diagnostic may pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add a dispatch-section case with OPENAI_API_KEY set, mv-on-PATH prep failure, TEST_AGENT_BEHAVIOR=cursor-success; assert codex-env-key-failure Codex auth setup failed breadcrumb in wrapper log and sidecar, absent argv capture, and CODER_TOOL=cursor

### FINDING_2: Login auth-prep fallback case lacks cursor-success stub
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Concern**: The login-mode auth-prep failure test expects Cursor fallback success but does not configure the agent stub to make Cursor succeed, so the test may fail for the wrong reason.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add TEST_AGENT_BEHAVIOR=cursor-success to that auth-prep failure invocation before asserting CODER_TOOL=cursor

### FINDING_3: mv failure fixture can pollute later fallback writes
- **Reviewer(s)**: Codex-Pragmatic, Codex-Requirements
- **Severity**: important
- **Concern**: An always-failing `mv` stub may trigger Codex auth-prep failure but also break later review-and-fix atomic writes after Cursor fallback, making the harness fail for fixture pollution rather than the intended auth branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Specify a conditional/delegating mv stub that fails only for the temp larch-codex-review-fix-home config rewrite and delegates all other mv calls to /bin/mv
  - From Codex-Requirements: If using an mv stub, make it fail only the temp CODEX_HOME config rewrite and delegate other paths to /bin/mv; otherwise use a prep-failure mechanism that does not shadow mv globally.

### FINDING_4: Legacy config-strip probe targets wrong auth branch
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: The planned legacy `env_key` stripping fixture sets `OPENAI_API_KEY`, which exercises the env-key branch instead of the intended login/auth.json fallback branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Run this capture case with OPENAI_API_KEY unset or empty and HOME containing .codex/auth.json plus the legacy config; keep the captured-config and original-fixture assertions.

### FINDING_5: Login auth-prep failure cleanup is not directly asserted
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: The planned cleanup check relies on Codex being spawned, but login auth-prep failure skips Codex, so leaked temporary review-fix homes could survive while Cursor fallback still succeeds.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add a before/after snapshot around the login auth-prep failure case's private TMPDIR and fail only on new larch-codex-review-fix-home.* survivors.

### FINDING_6: Login auth-prep failure needs negative env-key diagnostic assertions
- **Reviewer(s)**: Cursor-dyn-auth-isolation
- **Severity**: important
- **Concern**: The login auth-prep failure case only checks for the login-path diagnostic and would still pass if it also emitted the env-key failure diagnostic, creating misleading operator guidance.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-auth-isolation: Add grep -Fq codex-env-key-failure on wrapper log and sidecar with inverted expectation (must not match) alongside the auth-setup assertion

### FINDING_7: Env-key dispatch-failure fallback cleanup is not pinned
- **Reviewer(s)**: Codex-dyn-auth-isolation
- **Severity**: important
- **Concern**: The cleanup assertion can be satisfied by a Codex-success path without proving that the env-key dispatch-failure Cursor fallback removes the temporary CODEX_HOME before falling through.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-auth-isolation: Reuse the env-key dispatch-failure fallback case: also set TEST_AGENT_CODEX_HOME_FILE, then assert the captured path no longer exists after run_review_and_fix returns

### FINDING_8: model_provider exact-count assertion conflicts with split multiline fixtures
- **Reviewer(s)**: Cursor-dyn-fixture-hygiene
- **Severity**: important
- **Concern**: If multiline corruption is moved into separate fixtures, the remaining `strip-edge-config.toml` assertions may still expect one `model_provider` selector even though table-only stripping can remove all matching selector lines.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-fixture-hygiene: State whether `strip-edge-config.toml` keeps the multiline verbatim line; if multiline moves out, assert count 0 (or scope `grep -Fxc` to non-multiline lines only)
