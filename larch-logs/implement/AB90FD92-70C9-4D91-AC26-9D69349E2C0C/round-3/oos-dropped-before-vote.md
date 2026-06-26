### OOS_1: [OUT_OF_SCOPE] Missing run_main test for live targeted-fetch verdict-gate wiring
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: important
- **Concern**: The plan called for a `run_main` integration test where live `_fetch_filed_oos_issue_details()` fails under `--ground-truth-verdict`. Coverage today exercises `__fetch_failed__` via offline `--filed-issue-details-json` (`test_ground_truth_verdict_targeted_fetch_degradation_blocks_go`) and `run_main` enrichment degradation (`test_run_main_verdict_promotes_issue_enrichment_degraded`), but not the live targeted-fetch → verdict-gate wiring. A regression that drops `targeted_fetch_degraded=_ground_truth_targeted_fetch_degraded(details)` in `run_main` would not fail CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add a monkeypatched `run_main` test mirroring the enrichment test: fixture with filed OOS candidates, mock `_fetch_filed_oos_issue_details` returning `{N: {"__fetch_failed__": True}}`, assert exit `1`, verdict corpus block, and stderr `ERROR=`.

### OOS_2: [OUT_OF_SCOPE] Ground-truth caches omit log-tree content fingerprinting
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: `_GROUND_TRUTH_ROW_CACHE` / `_GROUND_TRUTH_FILED_CACHE` keys omit log-tree content fingerprinting. In a long-lived Python process, mutating `larch-logs` between verdict calls with identical filter argv can reuse stale rows, counts, or filed-OOS joins. Normal CLI one-shot use is fine; repeated in-process calls are not.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Document one-shot expectation, or add an opt-in cache-bust / mtime-aware key if in-process reuse is intended.

### OOS_3: [OUT_OF_SCOPE] README omits two-step human GO contract for analyze-issues verdict
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: The `/analyze-issues` row in `README.md:134` describes mechanical verdict gating but not the second step: human **GO** recorded in `docs/ground-truth-verdict.md` before shipping token allocation (#4771). `docs/skills.md`, the skill, and `docs/point-competition.md` state the two-step contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add one sentence to the README description aligning with those docs.

