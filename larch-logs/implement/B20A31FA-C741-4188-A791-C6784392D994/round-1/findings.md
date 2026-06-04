### FINDING_1: Missing launch-review Codex auth-mode harness coverage
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-codex-auth-flow-output.txt
- **Severity**: important
- **Concern**: `scripts/test-launch-review.sh` was not extended for the new Codex auth argv behavior, leaving env-key wiring, login fallback strip/symlink behavior, and auth-prep failure handling unguarded.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-codex-auth-flow-output.txt: Address the concern above.

### FINDING_2: Missing review-and-fix Codex dispatch auth tests
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-codex-auth-flow-output.txt
- **Severity**: important
- **Concern**: `skills/review-and-fix/scripts/test-review-and-fix.sh` lacks coverage for the new temp `CODEX_HOME`, shared auth helpers, env-key argv, fallback behavior, cleanup, and failure breadcrumb behavior in Step 5 Codex dispatch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-codex-auth-flow-output.txt: Address the concern above.

### FINDING_3: Missing check-reviewers probe auth/cache harness coverage
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-codex-auth-flow-output.txt, dyn-probe-cache-output.txt
- **Severity**: important
- **Concern**: `scripts/test-check-reviewers.sh` does not cover the new env-key probe matrix, stale stamp bypass behavior, trust/auth `-c` argv, helper failure handling, temp `CODEX_HOME` cleanup, or legacy config strip behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-codex-auth-flow-output.txt, dyn-probe-cache-output.txt: Address the concern above.

### FINDING_4: Login config strip misses larch selectors after TOML tables
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-bash-argv-output.txt, dyn-toml-strip-output.txt
- **Severity**: important
- **Concern**: `external_strip_codex_larch_env_provider` leaves top-level-looking `model_provider = "openai-larch-env"` or `env_key = "OPENAI_API_KEY"` lines after the first TOML table header, so login fallback can symlink `auth.json` while stale env-key selectors remain in config.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-bash-argv-output.txt, dyn-toml-strip-output.txt: Address the concern above.

### FINDING_5: Env-key implement launcher still merges larch-owned disk config artifacts
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `scripts/launch-codex-implement.sh` appends user config on the env-key path without stripping larch-owned provider/env-key artifacts, allowing legacy disk selectors to coexist with `-c` overrides.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_6: Missing implementer auth-prep and fallback contract tests
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, dyn-codex-auth-flow-output.txt
- **Severity**: important
- **Concern**: `skills/implement/scripts/test-codex-implementer.sh` only covers the env-key argv success path and lacks unset/empty login fallback, auth-prep failure KV, trap ordering, and cleanup regression tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, dyn-codex-auth-flow-output.txt: Address the concern above.

### FINDING_7: Duplicated trust config argv construction
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `PROJECT_KEY` and `TRUST_CONFIG_ARG` construction is duplicated across multiple call sites, risking drift if quoting or trust behavior changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_8: Probe temp CODEX_HOME cleanup is not trap-backed
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, dyn-bash-argv-output.txt, dyn-probe-cache-output.txt
- **Severity**: important
- **Concern**: `scripts/check-reviewers.sh` removes probe temp homes only on normal return paths; signals or abnormal exits can orphan `/tmp/larch-codex-probe-home-*` directories containing copied config or auth symlinks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, dyn-bash-argv-output.txt, dyn-probe-cache-output.txt: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] launch-review auth-prep failure contract differs from other launchers
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, dyn-bash-argv-output.txt
- **Severity**: latent
- **Concern**: `scripts/launch-review.sh` exits non-zero on Codex auth-prep failure while implement/CI paths emit launcher KVs and exit 0, which may confuse collectors or retry logic.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, dyn-bash-argv-output.txt: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] Missing lib strip failure and post-table fixtures
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-toml-strip-output.txt
- **Severity**: important
- **Concern**: `scripts/test-lib-external-launcher-common.sh` does not cover strip failure, no-symlink fail-closed behavior, post-table selector retention, multiline string corruption, or related unsafe rewrite cases.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-toml-strip-output.txt: Address the concern above.

### FINDING_11: Missing CI launcher login/auth-prep test coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-codex-auth-flow-output.txt
- **Severity**: important
- **Concern**: `scripts/test-launch-codex-ci.sh` covers env-key success but not login branches, auth-prep failure, leak assertions, or `env -u OPENAI_API_KEY` isolation for non-env-key runtime cases.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, dyn-codex-auth-flow-output.txt: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] launch-review docs stale after auth behavior change
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `scripts/launch-review.md` does not describe the new Codex auth behavior, leaving operator-facing documentation stale.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_13: Probe config copy may retain literal secrets in temp home
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `scripts/check-reviewers.sh` copies `~/.codex/config.toml` into a temp `CODEX_HOME` without scrubbing non-larch secret fields, so misconfigured literal keys may persist under `/tmp` until cleanup.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_14: review-and-fix env-key failure breadcrumb is ambiguous or hidden
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-codex-auth-flow-output.txt
- **Severity**: important
- **Concern**: `review-and-fix.sh` logs env-key Codex failure mostly in sidecars and may emit the breadcrumb even after auth setup failure, making Cursor fallback look like a clean success or misclassifying setup failure as exec failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-codex-auth-flow-output.txt: Address the concern above.

### FINDING_15: [OUT_OF_SCOPE] Direct codex helpers remain outside shared auth surface
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-codex-auth-flow-output.txt
- **Severity**: latent
- **Concern**: `/research` and other direct `codex exec` helpers do not use the new shared auth helper, so `OPENAI_API_KEY` preference may not apply uniformly outside the scoped launcher surfaces.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, dyn-codex-auth-flow-output.txt: Address the concern above.

### FINDING_16: [OUT_OF_SCOPE] Redactor lacks explicit OPENAI_API_KEY value scrubbing
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `scripts/redact-secrets.sh` has `sk-*` patterns but no explicit `OPENAI_API_KEY=` value scrubber, so unusual key formats in vendor error output might survive.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_17: CI auth-prep setup failures are classified as auth verdicts
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `scripts/launch-codex-ci.sh` classifies `external_prepare_codex_auth` strip/rewrite setup failures as auth failures, which may cause CI-fix routing or retry logic to treat setup errors as quota/auth problems.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_18: Env-key cached true stamps can become stale after key rotation
- **Reviewer(s)**: dyn-codex-auth-flow-output.txt, dyn-probe-cache-output.txt
- **Severity**: important
- **Concern**: `scripts/check-reviewers.sh` bypasses stale env-key false stamps but still honors env-key true stamps until TTL expiry, so revoked or rotated API keys can leave `CODEX_PRESENT=true` while real launches fail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-codex-auth-flow-output.txt, dyn-probe-cache-output.txt: Address the concern above.

### FINDING_19: [OUT_OF_SCOPE] review-and-fix omits Codex model/effort argv parity
- **Reviewer(s)**: dyn-codex-auth-flow-output.txt, dyn-bash-argv-output.txt
- **Severity**: important
- **Concern**: `skills/review-and-fix/scripts/review-and-fix.sh` builds trust/auth args but does not include `agent-model-args.sh --tool codex --with-effort`, unlike the other launcher/probe surfaces.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-codex-auth-flow-output.txt, dyn-bash-argv-output.txt: Address the concern above.

### FINDING_20: review-and-fix temp CODEX_HOME cleanup is not trap-backed
- **Reviewer(s)**: dyn-bash-argv-output.txt
- **Severity**: important
- **Concern**: `run_coder_dispatch` removes its temp `CODEX_HOME` only on the linear path; interruption before cleanup can orphan temp auth state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-argv-output.txt: Address the concern above.

### FINDING_21: TOML strip can corrupt multiline strings or launcher instructions
- **Reviewer(s)**: dyn-toml-strip-output.txt
- **Severity**: important
- **Concern**: The line-oriented strip helper treats bracket-like lines inside multiline TOML strings or prepended `instructions` as real headers, so it can delete config/instruction content while still exiting successfully.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-toml-strip-output.txt: Address the concern above.

### FINDING_22: TOML strip does not handle array-of-tables larch provider headers
- **Reviewer(s)**: dyn-toml-strip-output.txt
- **Severity**: important
- **Concern**: The strip helper recognizes `[model_providers.openai-larch-env]` but not `[[model_providers.openai-larch-env]]`, allowing stale larch provider material to survive on the login path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-toml-strip-output.txt: Address the concern above.

### FINDING_23: [OUT_OF_SCOPE] Single-quoted legacy env_key forms are not stripped
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-toml-strip-output.txt
- **Severity**: latent
- **Concern**: Legacy larch selector lines using single-quoted or non-standard forms can survive the login strip path if such configs exist.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, dyn-toml-strip-output.txt: Address the concern above.

### FINDING_24: [OUT_OF_SCOPE] Branch-scope observation only
- **Reviewer(s)**: dyn-bash-argv-output.txt
- **Severity**: nit
- **Concern**: Reviewer noted which commits were on the branch and that the review targeted the Codex auth argv work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-argv-output.txt: Address the concern above.

### FINDING_25: [OUT_OF_SCOPE] Shared helper argv construction appears to match plan
- **Reviewer(s)**: dyn-bash-argv-output.txt
- **Severity**: nit
- **Concern**: Reviewer observed that shared auth argv construction and ordering in the main implement/review/CI launchers match the plan and existing tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-argv-output.txt: Address the concern above.

### FINDING_26: [OUT_OF_SCOPE] Pre-existing line-based instruction strip shares TOML blind spot
- **Reviewer(s)**: dyn-toml-strip-output.txt
- **Severity**: latent
- **Concern**: Existing instruction-stripping code in `launch-review.sh` and `launch-codex-implement.sh` shares the multiline-string blind spot, though the new helper broadens the exposure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-toml-strip-output.txt: Address the concern above.
