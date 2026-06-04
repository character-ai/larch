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


### FINDING_2: Env-key probe cache ignores fresh positive stamps
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Env-key mode bypasses fresh successful Codex probe stamps, causing repeated live probes on every `check-reviewers` run and adding latency/rate-limit risk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_23: Auth config argv helper lacks xtrace secret regression coverage
- **Reviewer(s)**: dyn-secret-eval-xtrace-output.txt
- **Severity**: latent
- **Concern**: The xtrace regression test only covers `external_codex_env_key_enabled`, not `external_codex_auth_config_args`, leaving future eval-related secret expansion regressions untested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-secret-eval-xtrace-output.txt: Address the concern above.


### FINDING_28: Probe cleanup removes temp homes before killing live probes
- **Reviewer(s)**: dyn-temp-home-lifecycle-output.txt
- **Severity**: latent
- **Concern**: `larch_probe_exit_cleanup` deletes registered probe temp dirs before killing probe PIDs, so abrupt exits can remove a live `CODEX_HOME` while the child is still running.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-temp-home-lifecycle-output.txt: Address the concern above.


### FINDING_7: Login config strip can leave legacy larch auth selectors
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-toml-strip-awk-output.txt
- **Severity**: important
- **Concern**: The login-branch TOML strip only reliably removes top-level larch `model_provider` / `env_key` entries before other tables; selectors after or inside other provider/profile tables can survive and interfere with auth.json login fallback.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-toml-strip-awk-output.txt: Address the concern above.


