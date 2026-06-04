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


