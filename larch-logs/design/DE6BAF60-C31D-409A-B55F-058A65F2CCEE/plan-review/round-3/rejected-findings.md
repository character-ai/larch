### [Plan Review] FINDING_4

### FINDING_4: Legacy config-strip probe targets wrong auth branch
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: The planned legacy `env_key` stripping fixture sets `OPENAI_API_KEY`, which exercises the env-key branch instead of the intended login/auth.json fallback branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Run this capture case with OPENAI_API_KEY unset or empty and HOME containing .codex/auth.json plus the legacy config; keep the captured-config and original-fixture assertions.


### [Plan Review] FINDING_6

### FINDING_6: Login auth-prep failure needs negative env-key diagnostic assertions
- **Reviewer(s)**: Cursor-dyn-auth-isolation
- **Severity**: important
- **Concern**: The login auth-prep failure case only checks for the login-path diagnostic and would still pass if it also emitted the env-key failure diagnostic, creating misleading operator guidance.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-auth-isolation: Add grep -Fq codex-env-key-failure on wrapper log and sidecar with inverted expectation (must not match) alongside the auth-setup assertion


### [Plan Review] FINDING_8

### FINDING_8: model_provider exact-count assertion conflicts with split multiline fixtures
- **Reviewer(s)**: Cursor-dyn-fixture-hygiene
- **Severity**: important
- **Concern**: If multiline corruption is moved into separate fixtures, the remaining `strip-edge-config.toml` assertions may still expect one `model_provider` selector even though table-only stripping can remove all matching selector lines.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-fixture-hygiene: State whether `strip-edge-config.toml` keeps the multiline verbatim line; if multiline moves out, assert count 0 (or scope `grep -Fxc` to non-multiline lines only)

