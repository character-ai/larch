### FINDING_1: Duplicate Codex env-key failure logging
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Multiple near-identical env-key failure log sites in `review-and-fix.sh` can drift between wrapper logs, telemetry sidecars, and `larch_err`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_2: Env-key probe cache ignores fresh positive stamps
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Env-key mode bypasses fresh successful Codex probe stamps, causing repeated live probes on every `check-reviewers` run and adding latency/rate-limit risk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_3: Removed Codex temp homes remain in cleanup registry
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `REVIEW_FIX_TMPDIRS` records Codex temp homes that are immediately removed, creating confusing dead cleanup entries.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: Inline TOML-strip awk is hard to test
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The large inline awk program in `lib-external-launcher-common.sh` makes strip edge cases harder to review and test independently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] Direct Codex exec paths do not use env-key auth helper
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Lint-fix and related direct Codex dispatch paths are outside the current plan and may still use ChatGPT billing or login auth even when `OPENAI_API_KEY` is set.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] Codex trust-config argv logic is duplicated
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `PROJECT_KEY` / `TRUST_CONFIG_ARG` logic is duplicated across Codex launch sites, making future trust-escape changes harder.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_7: Login config strip can leave legacy larch auth selectors
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-toml-strip-awk-output.txt
- **Severity**: important
- **Concern**: The login-branch TOML strip only reliably removes top-level larch `model_provider` / `env_key` entries before other tables; selectors after or inside other provider/profile tables can survive and interfere with auth.json login fallback.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-toml-strip-awk-output.txt: Address the concern above.

### FINDING_8: Env-key branch copies legacy larch auth config before argv overrides
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Env-key mode copies `~/.codex/config.toml` without stripping legacy larch `env_key` / `model_provider` entries, so file config and `-c` overrides may interact unpredictably.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_9: Auth config arg helper return value is ignored
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Call sites ignore `external_codex_auth_config_args` failures, so an invalid array name could silently skip auth `-c` arguments.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_10: Step 5 review-and-fix Codex auth harness coverage is missing
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `test-review-and-fix.sh` lacks planned stubbed Codex dispatch coverage for temp `CODEX_HOME`, auth argv, trusted-project overrides, auth-prep failure fallback, env-key failure breadcrumbs, and leak scans.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_11: Implement Codex launcher auth-failure and trap-ordering tests are missing
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `test-codex-implementer.sh` does not cover auth-prep failure or early nounset/trap-ordering failures, so temp-home leaks or missing launcher KV envelopes could regress unnoticed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_12: Launch-review auth and leak harness coverage is incomplete
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `test-launch-review.sh` only checks argv-level behavior and misses planned assertions for login auth.json symlink, env-key no-disk-provider mode, config stripping, and sentinel absence from meta/events/stderr.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_13: Check-reviewers probe lifecycle and strip tests are incomplete
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `test-check-reviewers.sh` lacks planned coverage for probe temp-home cleanup, config-strip fixtures, and non-aborting auth-prep failure behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_14: Env-key auth failure should be tested against login fallback
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: No automated test proves env-key mode avoids symlinking `auth.json` after Codex auth failure, leaving future fail-loud versus silent-login-fallback regressions uncaught.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_15: Probe cache migration may cause one-time extra probes
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: New Codex probe cache filenames ignore legacy `larch-codex-present` stamps, causing noisier Step 0 runs until old stamps expire.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_16: Copied Codex config may duplicate inline secret material
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Env-key dispatch copies full `~/.codex/config.toml` into temp storage without detecting inline API keys or secrets in non-larch tables.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] Login fallback may symlink auth.json containing plaintext keys
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Login fallback symlinks `~/.codex/auth.json`, which may contain plaintext keys if created with `codex login --with-api-key`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_18: CI Codex env-key events leak check is missing
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `test-launch-codex-ci.sh` lacks the planned sentinel absence check for `events.jsonl` on env-key CI runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_19: TOML strip multiline tracking misreads inline comments
- **Reviewer(s)**: dyn-toml-strip-awk-output.txt
- **Severity**: latent
- **Concern**: `update_multiline_state` scans trailing inline comments for triple quotes, which can incorrectly enter multiline mode and prevent later larch provider headers from being stripped.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-toml-strip-awk-output.txt: Address the concern above.

### FINDING_20: [OUT_OF_SCOPE] Consecutive multiline-token handling appears covered
- **Reviewer(s)**: dyn-toml-strip-awk-output.txt
- **Severity**: nit
- **Concern**: The scout’s consecutive-token question appears satisfied; odd/even occurrence counting works for same-line open/close pairs and whole-line comment fixtures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-toml-strip-awk-output.txt: Address the concern above.

### FINDING_21: [OUT_OF_SCOPE] Larch provider table skipping recovery appears covered
- **Reviewer(s)**: dyn-toml-strip-awk-output.txt
- **Severity**: nit
- **Concern**: Single- and double-bracket larch provider headers are both matched, and existing malformed-table fixtures exercise recovery to the next non-larch header.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-toml-strip-awk-output.txt: Address the concern above.

### FINDING_22: [OUT_OF_SCOPE] Existing comment fixture does not cover inline comment triples
- **Reviewer(s)**: dyn-toml-strip-awk-output.txt
- **Severity**: nit
- **Concern**: The current `# comment with """` fixture only validates whole-line comments, not inline comment text after assignments.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-toml-strip-awk-output.txt: Address the concern above.

### FINDING_23: Auth config argv helper lacks xtrace secret regression coverage
- **Reviewer(s)**: dyn-secret-eval-xtrace-output.txt
- **Severity**: latent
- **Concern**: The xtrace regression test only covers `external_codex_env_key_enabled`, not `external_codex_auth_config_args`, leaving future eval-related secret expansion regressions untested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-secret-eval-xtrace-output.txt: Address the concern above.

### FINDING_24: [OUT_OF_SCOPE] Env-key enabled Bash pattern is xtrace-safe
- **Reviewer(s)**: dyn-secret-eval-xtrace-output.txt
- **Severity**: nit
- **Concern**: The `${OPENAI_API_KEY+x}` / `${#OPENAI_API_KEY}` pattern is appropriate for Bash 3.2 and traces only presence/length, not the secret value.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-secret-eval-xtrace-output.txt: Address the concern above.

### FINDING_25: [OUT_OF_SCOPE] Auth config eval array-name validation is tight enough
- **Reviewer(s)**: dyn-secret-eval-xtrace-output.txt
- **Severity**: nit
- **Concern**: Current array-name validation blocks obvious eval injection for static call sites, though eval remains a future footgun for dynamic callers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-secret-eval-xtrace-output.txt: Address the concern above.

### FINDING_26: [OUT_OF_SCOPE] CMD_JSON records variable name, not secret value
- **Reviewer(s)**: dyn-secret-eval-xtrace-output.txt
- **Severity**: nit
- **Concern**: Env-key launches persist `-c` overrides including the `OPENAI_API_KEY` variable name in session-private metadata, but not the key value.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-secret-eval-xtrace-output.txt: Address the concern above.

### FINDING_27: [OUT_OF_SCOPE] Env auth still exposes key through inherited environment
- **Reviewer(s)**: dyn-secret-eval-xtrace-output.txt
- **Severity**: nit
- **Concern**: Env-key mode avoids putting the secret on argv, but the child necessarily inherits `OPENAI_API_KEY`, with inherent same-user environment visibility.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-secret-eval-xtrace-output.txt: Address the concern above.

### FINDING_28: Probe cleanup removes temp homes before killing live probes
- **Reviewer(s)**: dyn-temp-home-lifecycle-output.txt
- **Severity**: latent
- **Concern**: `larch_probe_exit_cleanup` deletes registered probe temp dirs before killing probe PIDs, so abrupt exits can remove a live `CODEX_HOME` while the child is still running.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-temp-home-lifecycle-output.txt: Address the concern above.

### FINDING_29: [OUT_OF_SCOPE] Implement launcher trap ordering appears satisfied
- **Reviewer(s)**: dyn-temp-home-lifecycle-output.txt
- **Severity**: nit
- **Concern**: `launch-codex-implement.sh` initializes cleanup state and installs the EXIT trap before auth prep, so auth-prep failure still removes `CODEX_HOME_DIR`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-temp-home-lifecycle-output.txt: Address the concern above.

### FINDING_30: [OUT_OF_SCOPE] Review-and-fix temp-home double cleanup is redundant but safe
- **Reviewer(s)**: dyn-temp-home-lifecycle-output.txt
- **Severity**: nit
- **Concern**: `review-and-fix.sh` avoids empty-path registration on `mktemp` failure, removes created Codex homes inline, and then re-removes them via EXIT cleanup; this is redundant but safe.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-temp-home-lifecycle-output.txt: Address the concern above.

### FINDING_31: [OUT_OF_SCOPE] Probe dir registry double cleanup is idempotent after normal return
- **Reviewer(s)**: dyn-temp-home-lifecycle-output.txt
- **Severity**: nit
- **Concern**: After normal probe completion, `PROBE_DIRS` may contain already-removed paths, but the EXIT cleanup’s second `rm -rf` is idempotent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-temp-home-lifecycle-output.txt: Address the concern above.

### FINDING_32: [OUT_OF_SCOPE] Launch-review trap registration pattern appears sound
- **Reviewer(s)**: dyn-temp-home-lifecycle-output.txt
- **Severity**: nit
- **Concern**: `launch-review.sh` initializes `CODEX_HOME_DIR` before registering the EXIT trap and creates the temp home later, matching the implement launcher pattern.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-temp-home-lifecycle-output.txt: Address the concern above.
