### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/test-review-and-fix.sh:45-59
- **Concern**: Plan omits env-key auth-prep failure harness case. Scenario: Production writes codex-env-key-failure setup breadcrumbs when OPENAI_API_KEY is set and external_prepare_codex_auth fails (review-and-fix.sh:326-328); plan item 2 covers only login-mode prep failure and item 4 covers post-prep dispatch failure, so regressions that drop the env-key setup breadcrumb or sidecar line before Cursor fallback would not fail CI
- **Proposed resolution**: Add a dispatch-section case with OPENAI_API_KEY set, mv-on-PATH prep failure, TEST_AGENT_BEHAVIOR=cursor-success; assert codex-env-key-failure Codex auth setup failed breadcrumb in wrapper log and sidecar, absent argv capture, and CODER_TOOL=cursor

### FINDING_2:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/test-review-and-fix.sh:117-137
- **Concern**: Login-mode auth-prep failure case expects cursor fallback but plan does not set the stub to make cursor succeed. Scenario: If implemented literally, TEST_AGENT_BEHAVIOR defaults to codex-success; after Codex auth prep fails, the cursor branch hits the stub default failure path, so CODER_TOOL=cursor is never emitted and the new harness case fails
- **Proposed resolution**: Add TEST_AGENT_BEHAVIOR=cursor-success to that auth-prep failure invocation before asserting CODER_TOOL=cursor

### FINDING_3:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/review-and-fix/scripts/test-review-and-fix.sh:321-1848
- **Concern**: Planned login auth-prep failure case permits a fail-all mv PATH stub even though the cursor fallback path still needs mv later. Scenario: A stub mirroring test-codex-implementer.sh can make Codex prep fail, then break review-and-fix summary/output writes that call mv, so the fallback-success assertion fails for the wrong reason
- **Proposed resolution**: Specify a conditional/delegating mv stub that fails only for the temp larch-codex-review-fix-home config rewrite and delegates all other mv calls to /bin/mv

### FINDING_4:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/check-reviewers.sh:211-214
- **Concern**: Legacy config-strip probe case is planned for the env-key branch instead of login fallback. Scenario: The plan sets OPENAI_API_KEY for the fixture that should validate stripping copied legacy env_key before auth.json login fallback; that exercises the env-key branch, so a mixed login temp config can still pass.
- **Proposed resolution**: Run this capture case with OPENAI_API_KEY unset or empty and HOME containing .codex/auth.json plus the legacy config; keep the captured-config and original-fixture assertions.

### FINDING_5:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/review-and-fix/scripts/review-and-fix.sh:267-332
- **Concern**: Review-and-fix temp-home cleanup is not pinned on the auth-prep failure path. Scenario: The planned TEST_AGENT_CODEX_HOME_FILE cleanup check only works after Codex is spawned; in auth-prep failure Codex is skipped, so a leaked larch-codex-review-fix-home.* directory can survive while Cursor fallback still succeeds.
- **Proposed resolution**: Add a before/after snapshot around the login auth-prep failure case's private TMPDIR and fail only on new larch-codex-review-fix-home.* survivors.

### FINDING_6:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: code-quality
- **Location**: skills/review-and-fix/scripts/review-and-fix.sh:814
- **Concern**: The proposed mv failure fixture can break later review-and-fix atomic writes. Scenario: An always-failing mv stub will force auth prep failure, but the same PATH also affects later mv -f calls used to write summaries after Cursor fallback, so the test may fail for harness pollution rather than the Codex auth branch.
- **Proposed resolution**: If using an mv stub, make it fail only the temp CODEX_HOME config rewrite and delegate other paths to /bin/mv; otherwise use a prep-failure mechanism that does not shadow mv globally.

### FINDING_7:
- **Reviewer(s)**: Cursor-dyn-auth-isolation
- **Severity**: important
- **Focus area**: security
- **Location**: plan.txt:45-49
- **Concern**: Login auth-prep failure case lacks negative assertion that codex-env-key-failure is absent. Scenario: When OPENAI_API_KEY is unset, run_coder_dispatch should emit only codex-auth-setup on prep failure; a regression that also logs codex-env-key-failure would still pass item 2's positive grep and mis-train operators to rotate API keys on a login-path failure
- **Proposed resolution**: Add grep -Fq codex-env-key-failure on wrapper log and sidecar with inverted expectation (must not match) alongside the auth-setup assertion

### FINDING_8:
- **Reviewer(s)**: Codex-dyn-auth-isolation
- **Severity**: important
- **Focus area**: security
- **Location**: <TMPDIR>/plan.txt:54-59; skills/review-and-fix/scripts/review-and-fix.sh:277-343
- **Concern**: Finding 1: review-and-fix CODEX_HOME cleanup assertion is not pinned to the cursor-fallback path. Scenario: The plan may satisfy line 59 with a codex-success dispatch while the env-key dispatch-failure fallback case at plan lines 54-58 never proves the temporary larch-codex-review-fix-home is removed before falling through to Cursor
- **Proposed resolution**: Reuse the env-key dispatch-failure fallback case: also set TEST_AGENT_CODEX_HOME_FILE, then assert the captured path no longer exists after run_review_and_fix returns

### FINDING_9:
- **Reviewer(s)**: Cursor-dyn-fixture-hygiene
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-lib-external-launcher-common.sh:135-155
- **Concern**: Exact-count `model_provider` assertion conflicts with splitting multiline fixtures. Scenario: Step 2 moves multiline corruption into separate temp configs; if lines 149-151 leave `strip-edge-config.toml`, `grep -Fxc 'model_provider = "openai-larch-env"'` expects 1 but post-table-only strip yields 0 (all selector lines are stripped, including nested `[model_providers.other]` at 143-144)
- **Proposed resolution**: State whether `strip-edge-config.toml` keeps the multiline verbatim line; if multiline moves out, assert count 0 (or scope `grep -Fxc` to non-multiline lines only)
