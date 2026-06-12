### OOS_6: [OUT_OF_SCOPE] analyze-issues docs point at deleted contract files
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-integration-output.txt
- **Severity**: nit
- **Concern**: The analyze-issues skill still points operators at deleted `scripts/*.md` contract files instead of the live Python modules and pytest harness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-integration-output.txt: Address the concern above.


### OOS_7: [OUT_OF_SCOPE] audit-runs skill prose still cites retired shell surfaces
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt, dyn-integration-output.txt
- **Severity**: nit
- **Concern**: The audit-runs skill still references deleted shell helpers, jq scan surfaces, deleted test harnesses, and deleted contract siblings despite step-level fences using Python CLI verbs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt, dyn-integration-output.txt: Address the concern above.


### OOS_8: [OUT_OF_SCOPE] release skill inventory references deleted helpers
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-integration-output.txt
- **Severity**: important
- **Concern**: The release skill intro and helper inventory still point operators at deleted shell helpers, deleted harnesses, and deleted contract docs instead of the live Python CLI and pytest surfaces.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-integration-output.txt: Address the concern above.


### OOS_9: [OUT_OF_SCOPE] audit-runs wire-contract tests are incomplete
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `python/test_audit_runs.py` lacks focused coverage for resolve-prs key order, bad argv stderr behavior, map-runs TSV shape, and Pacific timestamp KVs, so orchestration wire regressions may pass CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt: Address the concern above.


### OOS_10: [OUT_OF_SCOPE] classify-bump rules doc still names deleted shell implementation
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-integration-output.txt
- **Severity**: nit
- **Concern**: `classify-bump.md` still presents `classify-bump.sh` and `release-prepare.sh` as implementation or consumer surfaces, which can misroute maintainers after the Python migration.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, dyn-integration-output.txt: Address the concern above.


