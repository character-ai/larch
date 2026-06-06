### [Plan Review] FINDING_3

### FINDING_3: Negotiation Codex path omits trusted-project config
- **Reviewer(s)**: Codex-Arch, Codex-Pragmatic
- **Severity**: important
- **Concern**: The proposed ephemeral `CODEX_HOME` negotiation wiring does not explicitly pass the workspace trust config. Workspaces trusted only in the user’s normal Codex config may fail or prompt/refuse before the stdin prompt runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: When adding CODEX_AUTH_ARGS, also compute PROJECT_KEY from WORKSPACE and pass -c "$TRUST_CONFIG_ARG" before the auth args, matching check-reviewers.sh and the new launcher; generate the generic launcher trust arg from --workdir.
  - From Codex-Pragmatic: Compute the trust config from WORKSPACE and pass -c projects."<workspace>".trust_level="trusted" with the auth args; add this to the negotiation harness assertions


### [Plan Review] FINDING_4

### FINDING_4: Negotiation ephemeral CODEX_HOME drops config.toml
- **Reviewer(s)**: Cursor-Edge
- **Severity**: latent
- **Concern**: The inline negotiation auth path copies only `auth.json` into an ephemeral `CODEX_HOME`, unlike the existing reviewer check path that also preserves/strips `config.toml`. This can drop model/provider defaults or other user config used by the login path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: When copying `check-reviewers.sh:214-242`, include the `config.toml` copy/strip step from lines 211-213, or document login-path config loss as accepted.


### [Plan Review] FINDING_5

### FINDING_5: Codex exec auth lint checks file-scope helper presence instead of invocation wiring
- **Reviewer(s)**: Cursor-dyn-auth-surface
- **Severity**: important
- **Concern**: `scripts/lint-codex-exec-auth.sh` can pass a file merely because it references `external_prepare_codex_auth` somewhere, even if individual `codex exec` invocations do not expand `${CODEX_AUTH_ARGS[@]}`. This leaves OPENAI_API_KEY preference regressions undetected in branches such as negotiation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-auth-surface: Tighten rule (a): flag each non-comment codex exec line unless it is inside launch-codex-exec.sh, carries a pragma, or the same function/block also expands CODEX_AUTH_ARGS immediately before exec; drop file-scope helper-presence bypass


