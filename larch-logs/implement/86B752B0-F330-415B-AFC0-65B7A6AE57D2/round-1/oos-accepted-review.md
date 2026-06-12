### OOS_1: [OUT_OF_SCOPE] ci-wait still emits prose bail reasons
- **Reviewer(s)**: dyn-risk-integration-output.txt
- **Severity**: nit
- **Concern**: `scripts/ci-wait.sh` still emits prose `BAIL_REASON` values. Only `ci-decide.sh` tokens were normalized, so mixed prose and token surfaces remain in the CI wait stack.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-risk-integration-output.txt: Address the concern above.


### OOS_2: [OUT_OF_SCOPE] Prompt-side ledger KV parsing lacks mechanical wrapper protection
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Ledger recording for lint-fix and bash ship-pr depends on prompt-side parsing of emitted KVs. A missed parse can silently drop escalation events even when child scripts emit ledger-ready data.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


