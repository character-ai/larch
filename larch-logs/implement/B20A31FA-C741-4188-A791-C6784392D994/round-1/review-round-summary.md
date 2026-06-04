# Review Round 1

- Mode: `diff`
- 13 accepted, 3 rejected (3 exonerated)

## Accepted Findings

### FINDING_1: Missing launch-review Codex auth-mode harness coverage
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-codex-auth-flow-output.txt
- **Severity**: important
- **Concern**: `scripts/test-launch-review.sh` was not extended for the new Codex auth argv behavior, leaving env-key wiring, login fallback strip/symlink behavior, and auth-prep failure handling unguarded.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-codex-auth-flow-output.txt: Address the concern above.


### FINDING_11: Missing CI launcher login/auth-prep test coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-codex-auth-flow-output.txt
- **Severity**: important
- **Concern**: `scripts/test-launch-codex-ci.sh` covers env-key success but not login branches, auth-prep failure, leak assertions, or `env -u OPENAI_API_KEY` isolation for non-env-key runtime cases.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, dyn-codex-auth-flow-output.txt: Address the concern above.


### FINDING_14: review-and-fix env-key failure breadcrumb is ambiguous or hidden
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-codex-auth-flow-output.txt
- **Severity**: important
- **Concern**: `review-and-fix.sh` logs env-key Codex failure mostly in sidecars and may emit the breadcrumb even after auth setup failure, making Cursor fallback look like a clean success or misclassifying setup failure as exec failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-codex-auth-flow-output.txt: Address the concern above.


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


### FINDING_2: Missing review-and-fix Codex dispatch auth tests
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-codex-auth-flow-output.txt
- **Severity**: important
- **Concern**: `skills/review-and-fix/scripts/test-review-and-fix.sh` lacks coverage for the new temp `CODEX_HOME`, shared auth helpers, env-key argv, fallback behavior, cleanup, and failure breadcrumb behavior in Step 5 Codex dispatch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-codex-auth-flow-output.txt: Address the concern above.


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


### FINDING_6: Missing implementer auth-prep and fallback contract tests
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, dyn-codex-auth-flow-output.txt
- **Severity**: important
- **Concern**: `skills/implement/scripts/test-codex-implementer.sh` only covers the env-key argv success path and lacks unset/empty login fallback, auth-prep failure KV, trap ordering, and cleanup regression tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, dyn-codex-auth-flow-output.txt: Address the concern above.


### FINDING_8: Probe temp CODEX_HOME cleanup is not trap-backed
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, dyn-bash-argv-output.txt, dyn-probe-cache-output.txt
- **Severity**: important
- **Concern**: `scripts/check-reviewers.sh` removes probe temp homes only on normal return paths; signals or abnormal exits can orphan `/tmp/larch-codex-probe-home-*` directories containing copied config or auth symlinks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, dyn-bash-argv-output.txt, dyn-probe-cache-output.txt: Address the concern above.


