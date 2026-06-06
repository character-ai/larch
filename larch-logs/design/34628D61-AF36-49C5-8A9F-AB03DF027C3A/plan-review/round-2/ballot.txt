### FINDING_1: Negotiation Codex auth drops config/trust under ephemeral CODEX_HOME
- **Reviewer(s)**: Cursor-Edge, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Codex-Requirements, Codex-dyn-launcher-contracts
- **Severity**: important
- **Concern**: The proposed run-negotiation Codex auth path switches to an ephemeral `CODEX_HOME` but does not fully preserve the existing Codex config/trusted-project behavior, so login/env-key negotiation can fail or lose user configuration despite auth setup succeeding.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Add `project_key` / `trust_config_arg` and pass `-c "$trust_config_arg"` on the inline `codex exec` argv (same 3-line pattern as `launch-codex-ci.sh:184-186` / `review-and-fix.sh:302-316`); extend `test-run-negotiation-round.sh` to assert the flag
  - From Codex-Innovation: Add the same project_key/trust_config_arg construction used in check-reviewers.sh and pass -c "$trust_config_arg" before CODEX_AUTH_ARGS; pin it in test-run-negotiation-round.sh
  - From Cursor-Pragmatic: Spell out the full check-reviewers.sh:211-245 steps in the plan (cp config.toml when present; trust_config_arg from $WORKSPACE; -c "$trust_config_arg" before auth-args) and extend test-run-negotiation-round.sh to assert those argv tokens alongside the env-key/login cases
  - From Codex-Pragmatic: Copy ~/.codex/config.toml into codex_home before external_prepare_codex_auth so the shared helper can strip credentials while preserving existing config; add a small negotiation test for config preservation in env-key and login modes
  - From Codex-Requirements: Copy ~/.codex/config.toml into codex_home/config.toml before external_prepare_codex_auth, then add env-key/login tests that prove copied config is stripped and auth still works
  - From Codex-dyn-launcher-contracts: When adding the ephemeral CODEX_HOME branch, copy ~/.codex/config.toml when present and pass the same trust -c arg used by check-reviewers before the auth -c overrides

### FINDING_2: Auth retry loop can expose stale `.done` sentinel
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Concern**: The planned launcher auth-retry loop reuses `run-external-agent` without an inner sentinel, so a failed attempt can publish `OUTPUT.done` before a later retry succeeds, letting collectors race and classify the lane too early.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Invoke run-external-agent with RUN_EXTERNAL_AGENT_INNER_SENTINEL_SUFFIX=.inner.done inside the retry loop and promote .inner.done to .done only once after the final attempt, matching launch-review.sh; add a harness case where attempt 1 auth-fails and attempt 2 succeeds without an observable early .done

### FINDING_3: Planned auth linter stack may be unnecessary scope
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The plan adds a broad new lint stack in the same PR that rewires all known `codex exec` sites, creating extra maintenance surface without addressing an immediate uncovered call-site gap.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Defer the lint stack to a follow-up (or drop it): land launcher routing + negotiation inline auth + harnesses for those paths only; add the static guard only if a later change reintroduces raw `codex exec`

### FINDING_4: Launcher sidecars can be written for unsafe output paths
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Concern**: The new launcher validates `--output` only as absolute before writing preflight sidecars, so paths with newline/control/unsupported characters can corrupt metadata or create files that `run-external-agent` would reject later.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Validate OUTPUT with validate_meta_scalar_path or the same [A-Za-z0-9._/-] allowlist before any sidecar writes; add a bad-character argv test alongside the relative-output test

### FINDING_5: `agent-model-args.sh` preflight failure lacks collector sidecars
- **Reviewer(s)**: Codex-Requirements, Cursor-dyn-launcher-contracts
- **Severity**: important
- **Concern**: If `agent-model-args.sh` or a similar pre-`run-external-agent` step fails, the launcher can exit before writing `.diag`, `.meta`, and `.done`, causing background collection to wait until timeout instead of failing fast.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add a harness case that stubs agent-model-args.sh to fail and asserts the same truncated output, .diag, stub .meta, .done, LAUNCHER_EXIT, and wrapper-exit-0 contract
  - From Cursor-dyn-launcher-contracts: Mirror launch-review.sh:509-534 preflight bundle for agent-model-args failures (truncate output, .diag STATUS=FAILED, stub .meta, .done with rc) and exit 0; add harness case

### FINDING_6: Codex exec auth linter exemption is too broad
- **Reviewer(s)**: Codex-Requirements, Codex-dyn-auth-scope-mapper
- **Severity**: important
- **Concern**: The proposed linter exempts any shell file that references `external_prepare_codex_auth`, so unrelated raw `codex exec` invocations in the same file could bypass the guard.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Tighten the rule to require an explicit per-line pragma for direct exec lines, or narrow the documented guarantee to match the file-scope exemption
  - From Codex-dyn-auth-scope-mapper: Make the exemption command-block-local or require an explicit pragma for intentional raw covered launch sites, and add a fixture where a helper-referencing file with an unrelated raw codex exec fails.

### FINDING_7: Missing-codex pre-check can bypass collector sidecars
- **Reviewer(s)**: Cursor-dyn-launcher-contracts, Codex-dyn-launcher-contracts
- **Severity**: important
- **Concern**: Copying `launch-codex-ci`’s `command -v codex` pre-check into the new launcher can exit before `run-external-agent` writes `.meta`/`.done`, making collect-managed callers time out instead of observing immediate failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-launcher-contracts: Omit the launch-codex-ci binary pre-check from launch-codex-exec.sh and delegate to run-external-agent.sh health gate, or write the 444-463 preflight bundle before exit 0
  - From Codex-dyn-launcher-contracts: For launch-codex-exec, either let run-external-agent handle missing codex or make binary-missing use the same preflight bundle: truncate output, write .diag/.meta/.done with 127, emit LAUNCHER_EXIT=127, then exit 0

### FINDING_8: Negotiation protocol exit-code documentation will become stale
- **Reviewer(s)**: Codex-dyn-auth-scope-mapper
- **Severity**: important
- **Concern**: The plan updates negotiation auth behavior but leaves caller-facing protocol text saying exit 2 means reviewer command failure, even though Codex auth setup can now fail before `codex exec`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-auth-scope-mapper: Update this paragraph to say exit 2 covers Codex auth setup or reviewer command failure, while exit 3 remains Cursor preflight only.

### FINDING_9: Implement structure test pin will break after launcher reroute
- **Reviewer(s)**: Cursor-dyn-harness-contracts
- **Severity**: important
- **Concern**: `scripts/test-implement-structure.sh` still expects `lint-fix-loop.sh` to reference `run-external-agent.sh`, so routing through `launch-codex-exec.sh` can break CI despite correct wiring.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-harness-contracts: Add a plan step to repoint or relax this pin (e.g. require launch-codex-exec.sh and/or keep run-external-agent only inside the launcher) and update the harness in the same PR

### FINDING_10: Linter may miss env-assignment-prefixed `codex exec`
- **Reviewer(s)**: Codex-dyn-harness-contracts
- **Severity**: latent
- **Concern**: The proposed lint harness may not cover `CODEX_HOME=... codex exec` command shapes, allowing raw env-assignment-prefixed Codex calls without auth helpers to pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-harness-contracts: Add one `test-lint-codex-exec-auth.sh` fixture for an env-assignment-prefixed `codex exec` without the helper, and make the shell scanner skip leading env assignments before matching the command word
