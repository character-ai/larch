### FINDING_1: Duplicate Codex trust config construction across launch sites
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Multiple call sites independently escape `PROJECT_KEY` and construct trusted-project `-c` arguments while auth config args are centralized. Future path-escaping or trust-config fixes could land in some launchers but not probes or Step 5 dispatch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_2: Inline awk config stripping is hard to maintain
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: The login-branch config strip logic is a large inline awk program in a shared shell library, making future larch-owned config-strip changes risky and hard to fixture.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_3: Step 5 Codex dispatch is overly nested and duplicates failure logging
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `run_coder_dispatch` combines temp-home setup, auth prep, Codex execution, logging, and Cursor fallback in one long nested block. The duplicate env-key failure log branches increase drift risk and make cleanup/trap ordering harder to verify.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: Codex probe cleanup has redundant inline and trap paths
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `check-reviewers.sh` removes probe temp homes inline while also retaining those paths in `PROBE_DIRS` for the exit trap. This creates redundant cleanup and stale debug state after retries, even if it does not necessarily leak files.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_5: External launcher parity rule omits the new Codex env-key auth contract
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `.claude/rules/external-tool-launcher-parity.md` was not updated to describe shared `OPENAI_API_KEY` auth behavior across the wired Codex surfaces, so future launcher edits may miss probe or review-and-fix parity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_6: Whitespace-only OPENAI_API_KEY incorrectly enables env-key mode
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-auth-flow-output.txt
- **Severity**: important
- **Concern**: `external_codex_env_key_enabled` uses only a non-zero-length check, so whitespace-only `OPENAI_API_KEY` values skip login fallback and attempt env-key auth. A valid `~/.codex/auth.json` can be ignored until the variable is cleared.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-auth-flow-output.txt: Address the concern above.

### FINDING_7: Env-key path does not strip legacy larch-owned Codex config entries
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: In env-key mode, copied `~/.codex/config.toml` is not stripped of legacy `env_key` / `model_provider` lines. File config and argv `-c` overrides may conflict or produce confusing auth behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_8: Fresh false env-key probe stamps suppress retry within TTL
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-auth-flow-output.txt, dyn-probe-cache-output.txt, dyn-launcher-parity-output.txt
- **Severity**: important
- **Concern**: Env-key probe caching is auth-mode-aware, but a fresh `false` env-key stamp is still honored until TTL expiry. If an operator fixes or rotates `OPENAI_API_KEY` after a failed probe, `CODEX_PRESENT=false` can persist without a live re-probe.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-auth-flow-output.txt, dyn-probe-cache-output.txt, dyn-launcher-parity-output.txt: Address the concern above.

### FINDING_9: Review-and-fix env-key failure breadcrumbs are incomplete or misclassified
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-auth-flow-output.txt
- **Severity**: latent
- **Concern**: `review-and-fix.sh` does not consistently emit the intended env-key failure breadcrumb for all relevant Codex failures, while some pre-auth setup failures can be mislabeled as env-key auth failures. Operators may either miss the Codex failure reason before Cursor fallback or chase the wrong diagnosis.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, dyn-auth-flow-output.txt: Address the concern above.

### FINDING_10: Codex probe harness lacks required auth/trust/leak/config/cleanup assertions
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `scripts/test-check-reviewers.sh` omits several planned probe assertions, including auth and trust argv, sentinel leak checks, legacy config stripping, and temp-home cleanup. Probe regressions could ship without offline test failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_11: Review-and-fix harness misses login/auth failure and env-key fallback cases
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `skills/review-and-fix/scripts/test-review-and-fix.sh` does not assert planned login fallback auth-helper failure or env-key Codex failure logging before Cursor fallback. Step 5 dispatch regressions can slip through CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_12: Implement launcher lacks nounset/trap early auth failure test
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The plan-required early auth-prep failure test under `set -u` is missing for `launch-codex-implement.sh`. Trap or cleanup regressions could leak `/tmp/larch-codex-home-*` or break the KV envelope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_13: CI launcher auth-prep failure path lacks harness coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-launch-codex-ci.sh` does not cover `external_prepare_codex_auth` failure, so CI launcher auth strip/prep regressions may not be detected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_14: CI launcher sibling docs do not mention new auth-mode harness expectations
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `scripts/launch-codex-ci.md` does not document the new env-key/login argv and leak-check harness expectations, making future CI launcher changes harder to audit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_15: Env-key temp homes can duplicate literal secrets from copied Codex config
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-secret-surfaces-output.txt
- **Severity**: latent
- **Concern**: Env-key launches and new probe/review-and-fix call sites copy `~/.codex/config.toml` into ephemeral `/tmp` homes before or without stripping literal credential assignments. Operators who previously stored key material in config may have it duplicated into temp homes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, dyn-secret-surfaces-output.txt: Address the concern above.

### FINDING_16: Implement launcher login fallback symlink behavior is under-tested
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Implement launcher tests for unset/empty env-key mode do not assert that an existing `~/.codex/auth.json` is symlinked into the temp home, unlike the review launcher tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_17: SECURITY.md overclaims that env-key values cannot appear in Codex telemetry
- **Reviewer(s)**: dyn-secret-surfaces-output.txt
- **Severity**: important
- **Concern**: The new SECURITY.md text says key values never appear in Codex event streams or probe output, but larch does not sanitize all Codex CLI stderr/events sinks before capture. Upstream failures could include sensitive text in session-local artifacts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-secret-surfaces-output.txt: Address the concern above.

### FINDING_18: Codex env-key process-environment visibility is undocumented
- **Reviewer(s)**: dyn-secret-surfaces-output.txt
- **Severity**: latent
- **Concern**: Env-key auth intentionally leaves `OPENAI_API_KEY` in the child process environment, which can be visible to same-UID or host-level introspection. SECURITY.md and configuration docs do not document this Codex-specific exposure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-secret-surfaces-output.txt: Address the concern above.

### FINDING_19: Codex review launcher can orphan temp home on model-args failure
- **Reviewer(s)**: dyn-temp-lifecycle-output.txt
- **Severity**: important
- **Concern**: On `launch-review.sh` Codex paths, `agent-model-args.sh` preflight failure disables the EXIT trap and exits without dispatcher cleanup. After this branch, the orphaned temp home may already contain copied config and possibly a symlinked `auth.json`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-temp-lifecycle-output.txt: Address the concern above.

### FINDING_20: Step 5 Codex coder dispatch omits model args
- **Reviewer(s)**: dyn-launcher-parity-output.txt
- **Severity**: important
- **Concern**: `review-and-fix.sh` passes trust and auth `-c` overrides to Codex but does not call `agent-model-args.sh --tool codex --with-effort`. `LARCH_CODEX_MODEL` therefore applies to launchers/probes but not Step 5 coder dispatch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-launcher-parity-output.txt: Address the concern above.

### FINDING_21: Operator docs still say Codex health probe has no model argv
- **Reviewer(s)**: dyn-launcher-parity-output.txt
- **Severity**: latent
- **Concern**: `docs/configuration-and-permissions.md` says the Codex health probe runs with no model argv, but the branch now forwards model args in `check-reviewers.sh`. Docs and behavior disagree.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-launcher-parity-output.txt: Address the concern above.

### FINDING_22: Review and CI sibling docs lack explicit Codex argv spine
- **Reviewer(s)**: dyn-launcher-parity-output.txt
- **Severity**: latent
- **Concern**: `launch-review.md` and `launch-codex-ci.md` describe auth mode but not full Codex argv ordering, unlike `launch-codex-implement.md`. This weakens launcher parity auditing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-launcher-parity-output.txt: Address the concern above.

### OOS_1: [OUT_OF_SCOPE] Implement login symlink harness gap was marked not an introduced regression
- **Reviewer(s)**: dyn-auth-flow-output.txt
- **Severity**: latent
- **Concern**: Source marked this as a harness gap rather than an introduced product regression: implement tests do not assert login fallback creates an `auth.json` symlink, so the behavior is less pinned than review.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-auth-flow-output.txt: Address the concern above.

### OOS_2: [OUT_OF_SCOPE] Low-risk env-key config interaction observation
- **Reviewer(s)**: dyn-auth-flow-output.txt
- **Severity**: latent
- **Concern**: Source marked the env-key config interaction as low-risk/out-of-scope: legacy top-level `env_key` in copied config may remain, but argv provider overrides likely make this benign.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-auth-flow-output.txt: Address the concern above.

### OOS_3: [OUT_OF_SCOPE] CMD_JSON contains only env var name, not key value
- **Reviewer(s)**: dyn-secret-surfaces-output.txt
- **Severity**: nit
- **Concern**: No value leak was found in `CMD_JSON`; env-key mode serializes the variable name `OPENAI_API_KEY`, matching the existing retry-state sensitivity policy.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-secret-surfaces-output.txt: Address the concern above.

### OOS_4: [OUT_OF_SCOPE] Secret-safe detection is implemented correctly
- **Reviewer(s)**: dyn-secret-surfaces-output.txt
- **Severity**: nit
- **Concern**: Source observed that detection uses presence/length checks without expanding the key value, and harnesses assert sentinel values do not leak.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-secret-surfaces-output.txt: Address the concern above.

### OOS_5: [OUT_OF_SCOPE] Login fallback auth.json secret semantics predate this branch
- **Reviewer(s)**: dyn-secret-surfaces-output.txt
- **Severity**: latent
- **Concern**: Login fallback still symlinks `auth.json`, which may contain plaintext key material if created that way, but this behavior predates the branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-secret-surfaces-output.txt: Address the concern above.

### OOS_6: [OUT_OF_SCOPE] Uncovered Codex paths are unchanged
- **Reviewer(s)**: dyn-secret-surfaces-output.txt
- **Severity**: latent
- **Concern**: Direct `/research` and other uncovered Codex lanes still use prior auth behavior and were not changed by this diff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-secret-surfaces-output.txt: Address the concern above.

### OOS_7: [OUT_OF_SCOPE] Review-and-fix temp-home lifecycle appears sound
- **Reviewer(s)**: dyn-temp-lifecycle-output.txt
- **Severity**: nit
- **Concern**: Source found that review-and-fix temp homes are removed inline with the script EXIT trap as backstop; no leak was found on paths added by the branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-temp-lifecycle-output.txt: Address the concern above.

### OOS_8: [OUT_OF_SCOPE] Check-reviewers probe cleanup appears sound
- **Reviewer(s)**: dyn-temp-lifecycle-output.txt
- **Severity**: nit
- **Concern**: Source found every probe return path inline-removes the temp home; stale `PROBE_DIRS` entries only cause redundant exit-time cleanup, not leaks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-temp-lifecycle-output.txt: Address the concern above.

### OOS_9: [OUT_OF_SCOPE] Implement launcher early auth-prep trap issue appears fixed
- **Reviewer(s)**: dyn-temp-lifecycle-output.txt
- **Severity**: nit
- **Concern**: Source observed that moving the EXIT trap and guarding unset variables fixes the early auth-prep/nounset trap failure mode in production code.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-temp-lifecycle-output.txt: Address the concern above.

### OOS_10: [OUT_OF_SCOPE] CI launcher temp lifecycle appears sound
- **Reviewer(s)**: dyn-temp-lifecycle-output.txt
- **Severity**: nit
- **Concern**: Source found the CI launcher installs the trap before auth prep and still runs cleanup on auth-prep failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-temp-lifecycle-output.txt: Address the concern above.

### OOS_11: [OUT_OF_SCOPE] Temp cleanup harness gap without demonstrated runtime leak
- **Reviewer(s)**: dyn-temp-lifecycle-output.txt
- **Severity**: latent
- **Concern**: Source marked this as an acceptance/harness gap, not a demonstrated leak: tests do not assert leftover probe or review-and-fix temp homes after all relevant scenarios.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-temp-lifecycle-output.txt: Address the concern above.

### OOS_12: [OUT_OF_SCOPE] Probe trust argv harness gap
- **Reviewer(s)**: dyn-probe-cache-output.txt
- **Severity**: latent
- **Concern**: Source marked the missing probe `trust_level="trusted"` argv assertion as out-of-scope; implementation appears correct but CI would not catch that regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-probe-cache-output.txt: Address the concern above.

### OOS_13: [OUT_OF_SCOPE] Legacy pre-branch probe stamps are harmless
- **Reviewer(s)**: dyn-probe-cache-output.txt
- **Severity**: nit
- **Concern**: Old unsplit probe stamp files are no longer read after auth-mode-specific stamp names; they may remain briefly but are harmless.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-probe-cache-output.txt: Address the concern above.

### OOS_14: [OUT_OF_SCOPE] Launcher argv asymmetries are intentional
- **Reviewer(s)**: dyn-launcher-parity-output.txt
- **Severity**: nit
- **Concern**: Source observed that differences such as `--full-auto`, `--sandbox read-only`, `--add-dir`, and probe omissions match the plan and parity rule.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-launcher-parity-output.txt: Address the concern above.

### OOS_15: [OUT_OF_SCOPE] Auth-prep failure exit semantics predate this branch
- **Reviewer(s)**: dyn-launcher-parity-output.txt
- **Severity**: nit
- **Concern**: Implement/CI, review, and review-and-fix have different auth-prep failure exit semantics, but the source marked this as preexisting and not a new argv-ordering regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-launcher-parity-output.txt: Address the concern above.

### OOS_16: [OUT_OF_SCOPE] Trust/auth/output ordering is otherwise consistent
- **Reviewer(s)**: dyn-launcher-parity-output.txt
- **Severity**: nit
- **Concern**: Source observed that among the five wired call sites, trust/auth/output ordering is consistent where model args exist; the main outlier is the in-scope review-and-fix model-args omission.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-launcher-parity-output.txt: Address the concern above.
