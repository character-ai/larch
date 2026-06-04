# Review Round 2

- Mode: `diff`
- 16 accepted, 8 rejected (8 exonerated)

## Accepted Findings

### FINDING_1: launch-review Codex auth harness coverage is missing
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-auth-secrets-output.txt, dyn-launcher-parity-output.txt
- **Severity**: important
- **Concern**: `scripts/launch-review.sh --tool codex` now wires temp `CODEX_HOME`, auth prep, auth `-c` argv, and env-key/login behavior, but `scripts/test-launch-review.sh` lacks the required env-set/env-unset/env-empty, login-strip, auth-prep failure, and sentinel leak assertions. Regressions in argv shape, `auth.json` symlinking, fallback, or secret leakage on the review path could ship without CI detection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-auth-secrets-output.txt, dyn-launcher-parity-output.txt: Address the concern above.


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


### FINDING_2: review-and-fix Codex auth harness coverage is missing
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-auth-secrets-output.txt, dyn-launcher-parity-output.txt, dyn-fallback-observability-output.txt
- **Severity**: important
- **Concern**: Step 5 Codex dispatch in `skills/review-and-fix/scripts/review-and-fix.sh` gained temp `CODEX_HOME`, config copy, shared auth prep, auth argv overrides, and env-key failure breadcrumbs, but `test-review-and-fix.sh` lacks env-key/login/auth-failure/sentinel/fallback/cleanup coverage. Regressions in fallback observability, cleanup, auth argv, or secret leakage could ship undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-auth-secrets-output.txt, dyn-launcher-parity-output.txt, dyn-fallback-observability-output.txt: Address the concern above.


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


### FINDING_3: strip-failure fail-closed behavior lacks a helper test
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, dyn-auth-secrets-output.txt, dyn-toml-stripper-output.txt
- **Severity**: important
- **Concern**: `external_prepare_codex_auth` has no unit test proving that a strip failure returns nonzero and does not create/symlink `auth.json`. If strip logic regresses, login fallback could run with an unstripped env-key config or mixed auth state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, dyn-auth-secrets-output.txt, dyn-toml-stripper-output.txt: Address the concern above.


### FINDING_30: probe cache acceptance case lacks test coverage
- **Reviewer(s)**: dyn-probe-cache-output.txt
- **Severity**: important
- **Concern**: `scripts/test-check-reviewers.sh` does not cover the case where a fresh login-mode `false` stamp exists, `OPENAI_API_KEY` is set, and a succeeding env-key probe should still emit `CODEX_PRESENT=true`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-probe-cache-output.txt: Address the concern above.


### FINDING_34: review-and-fix env-key Codex failure is not operator-visible when Cursor succeeds
- **Reviewer(s)**: dyn-fallback-observability-output.txt
- **Severity**: important
- **Concern**: when env-key Codex fails and Cursor fallback succeeds, failure details are written only to Codex-side artifacts while round KVs point at Cursor. The operator transcript may imply Cursor ran normally without making the enterprise-key Codex failure visible.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-fallback-observability-output.txt: Address the concern above.


### FINDING_7: stripper misses single-quoted or whitespace-variant larch config
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt, dyn-toml-stripper-output.txt
- **Severity**: important
- **Concern**: strip regexes only cover narrow double-quoted, whitespace-specific forms. Single-quoted values, no-space assignments, or spaced table headers can leave larch env-key selectors/provider tables in copied config during login fallback, causing mixed auth or wrong-account billing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt, dyn-toml-stripper-output.txt: Address the concern above.


