### FINDING_1:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/run-negotiation-round.sh:68-98
- **Concern**: Negotiation inline auth omits trusted-project `-c` override when switching to ephemeral `CODEX_HOME`. Scenario: Plan cites `check-reviewers.sh:214-242` but only wires auth helpers; today negotiation inherits trust from real `~/.codex/config.toml`, while an empty temp home drops that and `codex exec --full-auto` can fail workspace trust even when auth succeeds
- **Proposed resolution**: Add `project_key` / `trust_config_arg` and pass `-c "$trust_config_arg"` on the inline `codex exec` argv (same 3-line pattern as `launch-codex-ci.sh:184-186` / `review-and-fix.sh:302-316`); extend `test-run-negotiation-round.sh` to assert the flag

### FINDING_2:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/launch-codex-exec.sh planned; scripts/run-external-agent.sh:152-168; scripts/launch-review.sh:571-573
- **Concern**: Planned auth-retry loop reuses run-external-agent without the inner-sentinel pattern. Scenario: Each failed inner run-external-agent attempt writes OUTPUT.done before launch-codex-exec decides to retry; collect-agent-results can observe that stale sentinel and classify the lane failed while the launcher is still retrying, causing early collection and racey results
- **Proposed resolution**: Invoke run-external-agent with RUN_EXTERNAL_AGENT_INNER_SENTINEL_SUFFIX=.inner.done inside the retry loop and promote .inner.done to .done only once after the final attempt, matching launch-review.sh; add a harness case where attempt 1 auth-fails and attempt 2 succeeds without an observable early .done

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:47-57,107-113
- **Concern**: `lint-codex-exec-auth` adds a full lint script, sibling `.md`, harness, Makefile target, pre-commit hook, and `docs/linting.md` rows in the same PR that already rewrites every known unwired `codex exec` call site. Scenario: The six-site sweep makes the guard redundant for landing correctness; ~400+ lines of new enforcement surface is scope beyond the #3475 auth-wire minimum and expands ongoing parity/CI maintenance without fixing a gap the sweep leaves open
- **Proposed resolution**: Defer the lint stack to a follow-up (or drop it): land launcher routing + negotiation inline auth + harnesses for those paths only; add the static guard only if a later change reintroduces raw `codex exec`

### FINDING_4:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/run-negotiation-round.sh:68-93
- **Concern**: Proposed inline Codex auth setup creates ephemeral CODEX_HOME but the detailed launch shape omits the trusted-project -c arg. Scenario: A login-mode or env-key negotiation run no longer sees the user's real ~/.codex project trust config, so codex exec --full-auto can fail on an untrusted workspace before producing a response
- **Proposed resolution**: Add the same project_key/trust_config_arg construction used in check-reviewers.sh and pass -c "$trust_config_arg" before CODEX_AUTH_ARGS; pin it in test-run-negotiation-round.sh

### FINDING_5:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: security
- **Location**: scripts/launch-codex-exec.sh:1
- **Concern**: New launcher validates --output only as absolute before writing preflight .diag/.meta/.done sidecars. Scenario: If a caller passes an absolute path with newline/control/unsupported bytes, the auth-prep failure path can corrupt line-oriented metadata or write sidecars for a path run-external-agent would later reject
- **Proposed resolution**: Validate OUTPUT with validate_meta_scalar_path or the same [A-Za-z0-9._/-] allowlist before any sidecar writes; add a bad-character argv test alongside the relative-output test

### FINDING_6:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/run-negotiation-round.sh:87-93 (proposed UPDATED)
- **Concern**: Negotiation inline auth wiring is underspecified versus its stated check-reviewers mirror. Scenario: Ephemeral CODEX_HOME without copying ~/.codex/config.toml and without a projects trust -c arg keyed to $WORKSPACE can drop login-side model config and fail full-auto trust for -C "$WORKSPACE"; proposed test-run-negotiation-round additions only pin provider -c args and would not catch the gap
- **Proposed resolution**: Spell out the full check-reviewers.sh:211-245 steps in the plan (cp config.toml when present; trust_config_arg from $WORKSPACE; -c "$trust_config_arg" before auth-args) and extend test-run-negotiation-round.sh to assert those argv tokens alongside the env-key/login cases

### FINDING_7:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: scripts/run-negotiation-round.sh:67-89
- **Concern**: Proposed Codex auth wiring moves negotiation into an ephemeral CODEX_HOME but does not copy ~/.codex/config.toml before external_prepare_codex_auth, unlike covered helpers such as scripts/check-reviewers.sh:211-214 and skills/review-and-fix/scripts/review-and-fix.sh:280-285. Scenario: Users with non-auth Codex config needed by negotiation lose it after this PR even though the plan claims login behavior is preserved
- **Proposed resolution**: Copy ~/.codex/config.toml into codex_home before external_prepare_codex_auth so the shared helper can strip credentials while preserving existing config; add a small negotiation test for config preservation in env-key and login modes

### FINDING_8:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:87-101
- **Concern**: Run-negotiation wiring omits copying ~/.codex/config.toml into the ephemeral CODEX_HOME before external_prepare_codex_auth. Scenario: Unlike check-reviewers.sh, the proposed negotiation path can drop user Codex config and skip the temp-config stripping path required by the shared env-key auth contract
- **Proposed resolution**: Copy ~/.codex/config.toml into codex_home/config.toml before external_prepare_codex_auth, then add env-key/login tests that prove copied config is stripped and auth still works

### FINDING_9:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:31-41,147-160
- **Concern**: Launcher pre-run failure testing covers auth-prep only, not agent-model-args.sh or other pre-run-external-agent failures. Scenario: If agent-model-args.sh fails in a background research/voter/judge launch and no .done/.meta bundle is written, collect-agent-results.sh can wait until timeout instead of failing fast
- **Proposed resolution**: Add a harness case that stubs agent-model-args.sh to fail and asserts the same truncated output, .diag, stub .meta, .done, LAUNCHER_EXIT, and wrapper-exit-0 contract

### FINDING_10:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: latent
- **Focus area**: security
- **Location**: plan.txt:16,47-57
- **Concern**: The linter promise says future raw codex exec sites fail, but the shell rule exempts any file that merely references external_prepare_codex_auth. Scenario: A new unauthenticated codex exec line added later to an already-wired file would pass lint because the helper appears elsewhere in the file
- **Proposed resolution**: Tighten the rule to require an explicit per-line pragma for direct exec lines, or narrow the documented guarantee to match the file-scope exemption

### FINDING_11:
- **Reviewer(s)**: Cursor-dyn-launcher-contracts
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/launch-codex-ci.sh:161-161
- **Concern**: agent-model-args.sh failure has no collect sidecar path in the copied mechanics. Scenario: Plan copies launch-codex-ci.sh:156-264 where agent-model-args runs bare under set -e; on failure the launcher exits before writing OUTPUT.done/.meta, so background fences stall until collect-agent-results SENTINEL_TIMEOUT
- **Proposed resolution**: Mirror launch-review.sh:509-534 preflight bundle for agent-model-args failures (truncate output, .diag STATUS=FAILED, stub .meta, .done with rc) and exit 0; add harness case

### FINDING_12:
- **Reviewer(s)**: Cursor-dyn-launcher-contracts
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/launch-codex-ci.sh:198-206
- **Concern**: Missing-codex pre-check omits .done for collect-managed callers. Scenario: Plan copies launch-codex-ci command -v codex branch (LAUNCHER_EXIT=127 then exit 1, no sidecars); today research/voter/judge fences call run-external-agent directly and its health-gate EXIT trap still writes OUTPUT.done
- **Proposed resolution**: Omit the launch-codex-ci binary pre-check from launch-codex-exec.sh and delegate to run-external-agent.sh health gate, or write the 444-463 preflight bundle before exit 0

### FINDING_13:
- **Reviewer(s)**: Codex-dyn-launcher-contracts
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/launch-codex-ci.sh:198-207; scripts/run-external-agent.sh:152-168; scripts/collect-agent-results.sh:293-316
- **Concern**: The plan says launch-codex-exec copies launch-codex-ci mechanics, but launch-codex-ci's binary-missing branch exits 1 without collector sidecars. Scenario: Background research/voter/judge callers would wait on <output>.done; a copied command-v codex precheck can exit before run-external-agent writes .meta/.done, causing collector timeout instead of immediate FAILED status
- **Proposed resolution**: For launch-codex-exec, either let run-external-agent handle missing codex or make binary-missing use the same preflight bundle: truncate output, write .diag/.meta/.done with 127, emit LAUNCHER_EXIT=127, then exit 0

### FINDING_14:
- **Reviewer(s)**: Codex-dyn-launcher-contracts
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/check-reviewers.sh:211-245; scripts/run-negotiation-round.sh:89-93
- **Concern**: The run-negotiation inline auth plan omits config copy and trusted-project args while claiming to mirror check-reviewers. Scenario: Current negotiation runs codex with the ambient ~/.codex config; the proposed ephemeral CODEX_HOME plus no copied config/trust arg can drop user config and trusted-project behavior for the stdin-piped path
- **Proposed resolution**: When adding the ephemeral CODEX_HOME branch, copy ~/.codex/config.toml when present and pass the same trust -c arg used by check-reviewers before the auth -c overrides

### FINDING_15:
- **Reviewer(s)**: Codex-dyn-auth-scope-mapper
- **Severity**: important
- **Focus area**: security
- **Location**: plan.txt:47-49
- **Concern**: The proposed linter accepts any shell file that merely references external_prepare_codex_auth, so a helper mention can bless an unrelated raw codex exec in the same file.. Scenario: A future edit to scripts/run-negotiation-round.sh or another helper-referencing wrapper could add a second codex exec without CODEX_HOME or external_codex_auth_config_args and still pass the new guard.
- **Proposed resolution**: Make the exemption command-block-local or require an explicit pragma for intentional raw covered launch sites, and add a fixture where a helper-referencing file with an unrelated raw codex exec fails.

### FINDING_16:
- **Reviewer(s)**: Codex-dyn-auth-scope-mapper
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/shared/external-reviewers.md:106-114
- **Concern**: The plan updates run-negotiation-round.md but leaves the negotiation protocol's caller-facing exit-code contract stale for the new Codex auth-prep failure path.. Scenario: After the proposed change, Codex auth setup can fail before codex exec but still exits 2, while this protocol says 2 means reviewer command failed and tells wrappers to disambiguate auth-vs-tool by code.
- **Proposed resolution**: Update this paragraph to say exit 2 covers Codex auth setup or reviewer command failure, while exit 3 remains Cursor preflight only.

### FINDING_17:
- **Reviewer(s)**: Cursor-dyn-harness-contracts
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-implement-structure.sh:295-296
- **Concern**: Pin still requires lint-fix-loop.sh to reference run-external-agent.sh. Scenario: After run_codex routes through launch-codex-exec.sh, the grep pin fails and make test-implement-structure breaks CI even if the launcher wiring is correct
- **Proposed resolution**: Add a plan step to repoint or relax this pin (e.g. require launch-codex-exec.sh and/or keep run-external-agent only inside the launcher) and update the harness in the same PR

### FINDING_18:
- **Reviewer(s)**: Codex-dyn-harness-contracts
- **Severity**: latent
- **Focus area**: security
- **Location**: scripts/check-reviewers.sh:240-245
- **Concern**: The proposed lint harness does not include the real env-assignment-prefixed Codex shape `CODEX_HOME=... codex exec`. Scenario: A first-command-word-only scanner can miss a new raw `CODEX_HOME=/tmp/x codex exec ...` call with no auth helper, letting make lint and pre-commit pass an unwired env-key bypass
- **Proposed resolution**: Add one `test-lint-codex-exec-auth.sh` fixture for an env-assignment-prefixed `codex exec` without the helper, and make the shell scanner skip leading env assignments before matching the command word
