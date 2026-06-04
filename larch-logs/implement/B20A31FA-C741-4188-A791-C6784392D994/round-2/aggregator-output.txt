### FINDING_1: launch-review Codex auth harness coverage is missing
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-auth-secrets-output.txt, dyn-launcher-parity-output.txt
- **Severity**: important
- **Concern**: `scripts/launch-review.sh --tool codex` now wires temp `CODEX_HOME`, auth prep, auth `-c` argv, and env-key/login behavior, but `scripts/test-launch-review.sh` lacks the required env-set/env-unset/env-empty, login-strip, auth-prep failure, and sentinel leak assertions. Regressions in argv shape, `auth.json` symlinking, fallback, or secret leakage on the review path could ship without CI detection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-auth-secrets-output.txt, dyn-launcher-parity-output.txt: Address the concern above.

### FINDING_2: review-and-fix Codex auth harness coverage is missing
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-auth-secrets-output.txt, dyn-launcher-parity-output.txt, dyn-fallback-observability-output.txt
- **Severity**: important
- **Concern**: Step 5 Codex dispatch in `skills/review-and-fix/scripts/review-and-fix.sh` gained temp `CODEX_HOME`, config copy, shared auth prep, auth argv overrides, and env-key failure breadcrumbs, but `test-review-and-fix.sh` lacks env-key/login/auth-failure/sentinel/fallback/cleanup coverage. Regressions in fallback observability, cleanup, auth argv, or secret leakage could ship undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-auth-secrets-output.txt, dyn-launcher-parity-output.txt, dyn-fallback-observability-output.txt: Address the concern above.

### FINDING_3: strip-failure fail-closed behavior lacks a helper test
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, dyn-auth-secrets-output.txt, dyn-toml-stripper-output.txt
- **Severity**: important
- **Concern**: `external_prepare_codex_auth` has no unit test proving that a strip failure returns nonzero and does not create/symlink `auth.json`. If strip logic regresses, login fallback could run with an unstripped env-key config or mixed auth state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, dyn-auth-secrets-output.txt, dyn-toml-stripper-output.txt: Address the concern above.

### FINDING_4: trusted-project config argv construction is duplicated
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `PROJECT_KEY` / `TRUST_CONFIG_ARG` construction is duplicated across five Codex launcher/probe call sites, so future escaping or formatting changes can drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: temp CODEX_HOME bootstrap is duplicated
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: temp `CODEX_HOME` setup logic is duplicated between `scripts/check-reviewers.sh` and `skills/review-and-fix/scripts/review-and-fix.sh`, risking lifecycle, copy-order, or error-handling drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_6: probe cleanup uses overlapping strategies
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/check-reviewers.sh` mixes inline `rm -rf` with `PROBE_DIRS` EXIT cleanup, making auth-retry cleanup paths harder to reason about and leaving deleted paths accumulated in the trap list.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_7: stripper misses single-quoted or whitespace-variant larch config
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt, dyn-toml-stripper-output.txt
- **Severity**: important
- **Concern**: strip regexes only cover narrow double-quoted, whitespace-specific forms. Single-quoted values, no-space assignments, or spaced table headers can leave larch env-key selectors/provider tables in copied config during login fallback, causing mixed auth or wrong-account billing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt, dyn-toml-stripper-output.txt: Address the concern above.

### FINDING_8: embedded awk stripper is a complexity hotspot
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: the large embedded awk program in `scripts/lib-external-launcher-common.sh` is dense shared-library logic; future strip rules may make it harder to maintain safely.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] Step 5 Codex dispatch lacks model-args parity
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-launcher-parity-output.txt
- **Severity**: nit
- **Concern**: `skills/review-and-fix/scripts/review-and-fix.sh` passes trusted-project and auth overrides but does not call `agent-model-args.sh --tool codex`, unlike other covered Codex paths. Reviewers marked this as pre-existing/out-of-scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, dyn-launcher-parity-output.txt: Address the concern above.

### FINDING_10: stripper removes nested non-larch provider keys
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: strip logic can remove `env_key` or `model_provider = "openai-larch-env"` inside non-larch provider tables rather than only top-level larch-owned selector lines. Login fallback can therefore mutate unrelated provider configuration.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_11: review-and-fix skips env-key breadcrumb on auth-prep/setup failure
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-fallback-observability-output.txt
- **Severity**: important
- **Concern**: when `OPENAI_API_KEY` is set but temp setup, config copy, or `external_prepare_codex_auth` fails before Codex exec, `review-and-fix.sh` records only generic auth-setup failure and omits the planned redacted `codex-env-key-failure` breadcrumb before Cursor fallback.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-fallback-observability-output.txt: Address the concern above.

### FINDING_12: launch-review auth documentation update is missing
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: the plan required `scripts/launch-review.md` auth documentation updates, but reviewers reported they are absent from the diff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_13: env-key probe mode bypasses true cache hits
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `scripts/check-reviewers.sh` bypasses all env-key probe cache stamps, including fresh `true` hits, causing every session setup with env-key mode to re-run the Codex probe.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_14: implement launcher auth harness lacks failure/login cases
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `skills/implement/scripts/test-codex-implementer.sh` only covers the env-key happy path; auth failure traps, login fallback, unset/empty env behavior, and cleanup assertions are missing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_15: CI launcher auth harness lacks login/leak cases
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `scripts/test-launch-codex-ci.sh` only covers env-set argv. Login/unset/empty cases, events leak checks, and parent-env isolation are missing for the CI Codex path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_16: check-reviewers probe harness has auth/cleanup gaps
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `scripts/test-check-reviewers.sh` lacks coverage for probe cleanup paths, auth-helper failure, trust-only empty home behavior, and legacy env-key strip fixtures. Probe availability and temp-dir cleanup regressions could go undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_17: Codex harnesses do not consistently control OPENAI_API_KEY
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: several launcher harnesses do not explicitly unset `OPENAI_API_KEY` for login/default runs or set it only for env-key runs, making coverage flaky and allowing developer/CI environment state to select the wrong auth branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_18: auth-prep failure behavior is unpinned and divergent across launchers
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-launcher-parity-output.txt
- **Severity**: important
- **Concern**: auth-prep failure is not covered across the Codex launchers, and reviewers observed divergent contracts: review exits nonzero with review artifacts, while implement/CI emit their normal KV envelopes. Collectors could see inconsistent failure shapes for the same strip/symlink failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, dyn-launcher-parity-output.txt: Address the concern above.

### FINDING_19: copied temp Codex config may duplicate literal secrets
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-auth-secrets-output.txt
- **Severity**: latent
- **Concern**: covered paths copy full `~/.codex/config.toml` into temp `CODEX_HOME`. If an operator has misconfigured literal API keys or other secrets in that config, those secrets are duplicated under `/tmp`; documentation may overclaim that keys are not present in copied config files.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, dyn-auth-secrets-output.txt: Address the concern above.

### FINDING_20: [OUT_OF_SCOPE] research and direct codex exec helpers remain on old auth model
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-auth-secrets-output.txt, dyn-launcher-parity-output.txt
- **Severity**: latent
- **Concern**: `/research`, negotiation, lint-fix, and other direct `codex exec` paths are not wired through the shared env-key auth helper. Reviewers marked this as out-of-scope or explicitly documented for this branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, dyn-auth-secrets-output.txt, dyn-launcher-parity-output.txt: Address the concern above.

### FINDING_21: [OUT_OF_SCOPE] core env-key design positive observation
- **Reviewer(s)**: dyn-auth-secrets-output.txt
- **Severity**: nit
- **Concern**: the reviewer observed that the core env-key design avoids value expansion, passes only fixed `-c` tokens naming `OPENAI_API_KEY`, and avoids writing provider auth or symlinking `auth.json` in env-key mode.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-auth-secrets-output.txt: Address the concern above.

### FINDING_22: [OUT_OF_SCOPE] login fallback still symlinks plaintext auth.json
- **Reviewer(s)**: dyn-auth-secrets-output.txt
- **Severity**: latent
- **Concern**: when `OPENAI_API_KEY` is unset or empty, login fallback still symlinks `~/.codex/auth.json`, which may contain plaintext credentials. Reviewer marked this as pre-existing and unchanged.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-auth-secrets-output.txt: Address the concern above.

### FINDING_23: [OUT_OF_SCOPE] SECURITY.md Cursor argv text is stale
- **Reviewer(s)**: dyn-auth-secrets-output.txt
- **Severity**: nit
- **Concern**: `SECURITY.md` still describes Cursor `--api-key` argv persistence above the new Codex env-key section; reviewer marked this as stale relative to a prior issue and not introduced by this Codex change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-auth-secrets-output.txt: Address the concern above.

### FINDING_24: env-key branch keeps old larch env-key config on disk
- **Reviewer(s)**: dyn-launcher-parity-output.txt
- **Severity**: important
- **Concern**: on the env-key branch, `external_prepare_codex_auth` returns without stripping old larch-owned `model_provider` / `env_key` config from copied `~/.codex/config.toml`. Operators migrating from the old config pattern can still carry conflicting disk config alongside argv-only auth overrides.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-launcher-parity-output.txt: Address the concern above.

### FINDING_25: stripper multiline tracking is affected by comments
- **Reviewer(s)**: dyn-toml-stripper-output.txt
- **Severity**: important
- **Concern**: the awk stripper toggles multiline-string state on comment lines containing `"""` or `'''`. A comment can cause later top-level larch selector lines to be skipped rather than stripped, leaving mixed login/env-key config.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-toml-stripper-output.txt: Address the concern above.

### FINDING_26: malformed multiline content can make stripper delete unrelated config
- **Reviewer(s)**: dyn-toml-stripper-output.txt
- **Severity**: important
- **Concern**: while skipping the larch provider table, an unterminated multiline delimiter can prevent detection of subsequent table headers and cause the awk pass to drop the rest of the file, including unrelated providers/profiles.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-toml-stripper-output.txt: Address the concern above.

### FINDING_27: [OUT_OF_SCOPE] stripper requires writable config
- **Reviewer(s)**: dyn-toml-stripper-output.txt
- **Severity**: latent
- **Concern**: the strip helper requires write permission on `config.toml`; reviewers marked this as unlikely in production because launchers create writable temp homes, and failure would abort auth prep.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-toml-stripper-output.txt: Address the concern above.

### FINDING_28: [OUT_OF_SCOPE] stripper is intentionally not a full TOML parser
- **Reviewer(s)**: dyn-toml-stripper-output.txt
- **Severity**: latent
- **Concern**: residual TOML edge cases such as inline tables, dotted keys, or non-larch provider `env_key` entries remain because the helper is not a full parser. Reviewer marked this as outside the stated larch-owned artifact contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-toml-stripper-output.txt: Address the concern above.

### FINDING_29: probe cache can report stale login availability after env-key use
- **Reviewer(s)**: dyn-probe-cache-output.txt
- **Severity**: important
- **Concern**: after env-key probes, login-mode stamps are not refreshed or invalidated. If the operator later unsets the key while a stale fresh `codex-login` true stamp remains, `CODEX_PRESENT=true` can be reported without rechecking current login auth.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-probe-cache-output.txt: Address the concern above.

### FINDING_30: probe cache acceptance case lacks test coverage
- **Reviewer(s)**: dyn-probe-cache-output.txt
- **Severity**: important
- **Concern**: `scripts/test-check-reviewers.sh` does not cover the case where a fresh login-mode `false` stamp exists, `OPENAI_API_KEY` is set, and a succeeding env-key probe should still emit `CODEX_PRESENT=true`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-probe-cache-output.txt: Address the concern above.

### FINDING_31: [OUT_OF_SCOPE] probe temp-home lifecycle looks consistent but unasserted
- **Reviewer(s)**: dyn-probe-cache-output.txt
- **Severity**: nit
- **Concern**: reviewer observed the probe temp `CODEX_HOME` cleanup paths and EXIT trap look consistent, while noting the branch does not add harness assertions that probe-home directories are gone after each path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-probe-cache-output.txt: Address the concern above.

### FINDING_32: [OUT_OF_SCOPE] env-key cache semantics are stricter than docs prose
- **Reviewer(s)**: dyn-probe-cache-output.txt
- **Severity**: nit
- **Concern**: env-key mode bypasses all stamps, including fresh `true`, which matches fail-loud key-rotation intent but is broader than `scripts/check-reviewers.md` prose saying cached `false` is treated as a miss.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-probe-cache-output.txt: Address the concern above.

### FINDING_33: [OUT_OF_SCOPE] legacy probe stamps cause one-time extra probe
- **Reviewer(s)**: dyn-probe-cache-output.txt
- **Severity**: nit
- **Concern**: pre-branch `larch-codex-present-${USER}.stamp` files are no longer read; reviewer classified this as a one-time extra probe after upgrade, not incorrect availability signaling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-probe-cache-output.txt: Address the concern above.

### FINDING_34: review-and-fix env-key Codex failure is not operator-visible when Cursor succeeds
- **Reviewer(s)**: dyn-fallback-observability-output.txt
- **Severity**: important
- **Concern**: when env-key Codex fails and Cursor fallback succeeds, failure details are written only to Codex-side artifacts while round KVs point at Cursor. The operator transcript may imply Cursor ran normally without making the enterprise-key Codex failure visible.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-fallback-observability-output.txt: Address the concern above.

### FINDING_35: [OUT_OF_SCOPE] pre-existing Codex-to-Cursor waterfall hid failures
- **Reviewer(s)**: dyn-fallback-observability-output.txt
- **Severity**: latent
- **Concern**: Codex-to-Cursor fallback without env-key mode already hid Codex failure from stdout when Cursor succeeded; reviewer marked this broader waterfall-observability issue as pre-existing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-fallback-observability-output.txt: Address the concern above.
