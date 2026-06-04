### FINDING_12: Implement launcher tests miss auth symlink and early nounset/trap regression
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Implement launcher tests do not fully assert login `auth.json` symlink behavior or early auth-prep failure cleanup/KV behavior under `set -u`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_14: Env-key failure breadcrumbs are missing outside Step 5
- **Reviewer(s)**: dyn-auth-flow-output.txt
- **Severity**: important
- **Concern**: Implement, review, CI launchers and the health probe emit generic auth/runtime failure text when env-key auth fails, making API-key-path failures easy to misread as generic Codex or login-plan failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-auth-flow-output.txt: Address the concern above.


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


### FINDING_19: `launch-review.md` omits auth scope boundaries
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `scripts/launch-review.md` does not clearly state that its auth contract excludes review-and-fix Step 5 and direct `/research` Codex lanes, risking operator confusion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_2: Env-key auth can fail because config stripping runs before env-key branch
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-auth-flow-output.txt
- **Severity**: important
- **Concern**: `external_prepare_codex_auth` strips temp `config.toml` before checking `OPENAI_API_KEY` mode, so env-key auth can fail on an irrelevant config rewrite even though argv-only `-c` overrides should suffice.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-auth-flow-output.txt: Address the concern above.


### FINDING_20: Strip helper contract is underdocumented
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `external_strip_codex_literal_credentials` is not documented in the primary helper contract, so contributors may miss when copied credential lines are stripped.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


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


