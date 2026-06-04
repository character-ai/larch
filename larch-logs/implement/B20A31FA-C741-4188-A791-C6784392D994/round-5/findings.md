### FINDING_1: Duplicate TOML strip helper infrastructure
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: The two TOML strip helpers duplicate similar awk/multiline/comment-handling infrastructure, increasing the risk that a future fix lands in one path but not the other.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_2: Env-key auth can fail because config stripping runs before env-key branch
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-auth-flow-output.txt
- **Severity**: important
- **Concern**: `external_prepare_codex_auth` strips temp `config.toml` before checking `OPENAI_API_KEY` mode, so env-key auth can fail on an irrelevant config rewrite even though argv-only `-c` overrides should suffice.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-auth-flow-output.txt: Address the concern above.

### FINDING_3: `launch-review.sh` auth-prep failures use different exit envelope
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `launch-review.sh` exits non-zero on Codex auth-prep failure while implement/CI launchers emit structured failure KVs and exit 0, which may cause collectors to classify equivalent failures differently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_4: Helper docs disagree with strip control flow
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `scripts/lib-external-launcher-common.md` describes login-only stripping, but the implementation strips whenever temp `config.toml` exists, creating misleading guidance for future edits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_5: Trust config argument construction is duplicated
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `TRUST_CONFIG_ARG` construction is repeated across Codex call sites, risking future probe/review/implement trust-level drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_6: Duplicate Step 5 env-key failure logging
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `review-and-fix.sh` duplicates `codex-env-key-failure` logging for setup and dispatch failures, making future updates and log greps more fragile.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_7: Docs do not consistently describe whitespace-only `OPENAI_API_KEY`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-launcher-parity-output.txt
- **Severity**: nit
- **Concern**: Several operator-facing docs say “non-empty” or “unset/empty,” while runtime treats whitespace-only `OPENAI_API_KEY` as login fallback.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-launcher-parity-output.txt: Address the concern above.

### FINDING_8: Env-key predicate expands the secret value despite xtrace contract
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, dyn-secret-surface-output.txt
- **Severity**: important
- **Concern**: `external_codex_env_key_enabled` uses `case "$OPENAI_API_KEY"`, conflicting with the documented length-only/no-expansion contract and weakening xtrace leak guarantees; related tests/docs may not lock the intended behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, dyn-secret-surface-output.txt: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] Direct Codex lanes are not wired to shared env-key auth
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, dyn-auth-flow-output.txt
- **Severity**: latent
- **Concern**: Uncovered direct `codex exec` paths such as lint-fix, negotiation, and `/research` can still prefer login auth even when `OPENAI_API_KEY` is set.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, dyn-auth-flow-output.txt: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] Step 5 auth harness lacks required failure/fallback coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-auth-flow-output.txt
- **Severity**: important
- **Concern**: `test-review-and-fix.sh` does not fully cover login fallback, auth-prep failure, env-key dispatch failure breadcrumbs, and sentinel leak assertions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-auth-flow-output.txt: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] Codex probe harness misses plan acceptance cases
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-lifecycle-output.txt, dyn-probe-cache-output.txt
- **Severity**: important
- **Concern**: `test-check-reviewers.sh` lacks coverage for trust argv, env-key no-auth behavior, sentinel leaks, legacy strip behavior, and probe temp-home cleanup after retry/failure paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-lifecycle-output.txt, dyn-probe-cache-output.txt: Address the concern above.

### FINDING_12: Implement launcher tests miss auth symlink and early nounset/trap regression
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Implement launcher tests do not fully assert login `auth.json` symlink behavior or early auth-prep failure cleanup/KV behavior under `set -u`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_13: Auth-mode probe stamp behavior shift is undocumented/untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: New auth-mode-specific Codex probe stamps ignore old `larch-codex-present` stamps, causing upgraded installs to reprobe until new stamps populate without documented or asserted behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_14: Env-key failure breadcrumbs are missing outside Step 5
- **Reviewer(s)**: dyn-auth-flow-output.txt
- **Severity**: important
- **Concern**: Implement, review, CI launchers and the health probe emit generic auth/runtime failure text when env-key auth fails, making API-key-path failures easy to misread as generic Codex or login-plan failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-auth-flow-output.txt: Address the concern above.

### FINDING_15: Env-key positive probe cache can mask revoked or bad keys
- **Reviewer(s)**: dyn-auth-flow-output.txt, dyn-probe-cache-output.txt
- **Severity**: important
- **Concern**: A fresh `codex-env-key` positive stamp can be honored until TTL expiry even after the key is revoked, rotated, expired, or quota-blocked, so Step 0 can report Codex available before launch fails.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-auth-flow-output.txt, dyn-probe-cache-output.txt: Address the concern above.

### FINDING_16: Literal credential sanitizer misses multiline and nested/provider credentials
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-toml-strip-output.txt, dyn-secret-surface-output.txt
- **Severity**: important
- **Concern**: `external_strip_codex_literal_credentials` can leave multiline `api_key` bodies and provider-scoped literal credentials in temp `config.toml`, exposing secrets during launcher/probe/review-fix runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-toml-strip-output.txt, dyn-secret-surface-output.txt: Address the concern above.

### FINDING_17: Larch env-provider stripper misses unquoted or alternate selector forms
- **Reviewer(s)**: dyn-toml-strip-output.txt
- **Severity**: important
- **Concern**: `external_strip_codex_larch_env_provider` only removes quoted legacy selectors, so unquoted or alternate accepted TOML forms can survive into login fallback and force env-key provider selection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-toml-strip-output.txt: Address the concern above.

### FINDING_18: TOML rewriters lack post-rewrite validation
- **Reviewer(s)**: dyn-toml-strip-output.txt
- **Severity**: important
- **Concern**: The strip helpers can exit successfully after incomplete or unsafe rewrites, so callers may proceed with partially stripped credentials or inconsistent TOML instead of failing closed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-toml-strip-output.txt: Address the concern above.

### FINDING_19: `launch-review.md` omits auth scope boundaries
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `scripts/launch-review.md` does not clearly state that its auth contract excludes review-and-fix Step 5 and direct `/research` Codex lanes, risking operator confusion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_20: Strip helper contract is underdocumented
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `external_strip_codex_literal_credentials` is not documented in the primary helper contract, so contributors may miss when copied credential lines are stripped.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_21: CI launcher cleanup trap has latent nounset leak risk
- **Reviewer(s)**: dyn-bash-lifecycle-output.txt
- **Severity**: latent
- **Concern**: `launch-codex-ci.sh` uses bare `$MODEL_ARGS_TMP` in an EXIT trap under `set -u`, so future early-exit edits could skip cleanup and leak temp Codex homes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-lifecycle-output.txt: Address the concern above.

### FINDING_22: Probe cleanup leaves stale deleted paths in `PROBE_DIRS`
- **Reviewer(s)**: dyn-bash-lifecycle-output.txt
- **Severity**: nit
- **Concern**: `check-reviewers.sh` removes probe homes eagerly but leaves their paths in `PROBE_DIRS`, making future reuse of the array fragile.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-lifecycle-output.txt: Address the concern above.

### FINDING_23: Login-mode cached false can survive env-key success and block later login probe
- **Reviewer(s)**: dyn-probe-cache-output.txt
- **Severity**: important
- **Concern**: If login probing cached `false`, then env-key succeeds, and later `OPENAI_API_KEY` is cleared within TTL, the stale login `false` can suppress a live login probe even if login auth now works.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-probe-cache-output.txt: Address the concern above.

### FINDING_24: Launcher harnesses lack whitespace-only env-key cases
- **Reviewer(s)**: dyn-launcher-parity-output.txt
- **Severity**: latent
- **Concern**: Launcher-level tests cover set/unset/empty `OPENAI_API_KEY` but not whitespace-only values, leaving parity gaps around login fallback wiring.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-launcher-parity-output.txt: Address the concern above.

### FINDING_25: [OUT_OF_SCOPE] Cursor/run-external-agent metadata argv persistence
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-secret-surface-output.txt
- **Severity**: latent
- **Concern**: `run-external-agent.sh` / Cursor metadata can persist full child argv in `.meta`/`CMD_JSON`; this is pre-existing or documented, but remains a security surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, dyn-secret-surface-output.txt: Address the concern above.

### FINDING_26: [OUT_OF_SCOPE] TOML CRLF/table parsing edge cases
- **Reviewer(s)**: dyn-toml-strip-output.txt
- **Severity**: nit
- **Concern**: Table-header detection is not full TOML parsing and may miss CRLF-terminated or similar Windows-saved config edge cases.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-toml-strip-output.txt: Address the concern above.

### FINDING_27: [OUT_OF_SCOPE] Strip docs say top-level but implementation strips globally
- **Reviewer(s)**: dyn-toml-strip-output.txt
- **Severity**: latent
- **Concern**: Helper docs describe removing top-level legacy keys, while implementation strips matching lines globally, including provider tables.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-toml-strip-output.txt: Address the concern above.

### FINDING_28: [OUT_OF_SCOPE] CI model-args tempfile can leak if temp home creation fails
- **Reviewer(s)**: dyn-bash-lifecycle-output.txt
- **Severity**: latent
- **Concern**: `launch-codex-ci.sh` creates `MODEL_ARGS_TMP` before installing the cleanup trap, so a failure before trap setup can leak the tempfile.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-lifecycle-output.txt: Address the concern above.

### FINDING_29: [OUT_OF_SCOPE] Reverse auth-mode stamp transition lacks harness coverage
- **Reviewer(s)**: dyn-probe-cache-output.txt
- **Severity**: nit
- **Concern**: The probe harness lacks a test for clearing `OPENAI_API_KEY` after env-key success while a stale login-false stamp remains.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-probe-cache-output.txt: Address the concern above.

### FINDING_30: [OUT_OF_SCOPE] SECURITY.md older paragraph omits env-key precedence
- **Reviewer(s)**: dyn-secret-surface-output.txt
- **Severity**: nit
- **Concern**: A newer `SECURITY.md` section documents env-key auth, but an older external delegation paragraph still describes only `auth.json` symlink behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-secret-surface-output.txt: Address the concern above.
