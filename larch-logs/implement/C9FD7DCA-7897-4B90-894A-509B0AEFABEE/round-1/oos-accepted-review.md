### OOS_1: [OUT_OF_SCOPE] `larch-log.md` still documents committed NS-retry transcripts
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-risk-integration-output.txt, dyn-architecture-output.txt
- **Severity**: nit
- **Concern**: The docs still say NS-retry and dynamic Codex outputs remain committed, conflicting with the new debug-gated concise default and `reviewer_signals` audit carrier.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From dyn-risk-integration-output.txt: Rewrite the `write-round` retention section to match the concise default, explicitly list debug-gated families, and cross-link the `reviewer_signals` schema plus the migrated audit-scan behavior.
  - From dyn-architecture-output.txt: Rewrite the §write-round exclusion list at the top to match the debug-gated default and document the `reviewer_signals` schema as the sole default audit carrier; remove or relocate the stale NS-retry retention sentence.


### OOS_2: [OUT_OF_SCOPE] Concise audit note disrupts `docs/run-logs.md` section structure
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: A concise audit note appears inside the authoritative-sources list rather than under a normal section, making the docs structure awkward.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### OOS_3: [OUT_OF_SCOPE] Pruned combo env write does not reject embedded newlines
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `write_prune_decision_env` can write `PRUNED_COMBOS` values containing embedded newlines from manifest-derived keys, which could inject extra `KEY=value` lines into `prune-decision.env`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


