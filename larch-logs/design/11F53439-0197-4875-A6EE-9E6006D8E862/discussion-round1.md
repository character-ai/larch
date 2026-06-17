## Decision 1: code-review-tally.json multi-round semantics
- **Question**: For multi-round runs, should accepted_count / rejected_count / rounds be cumulative across rounds or final-round only?
- **Resolution**: Cumulative. `rounds` = total rounds run (= committed `round-*` dir count); `accepted_count` / `rejected_count` = totals across all rounds. Document this contract in `docs/run-logs.md`. Matches the already-correct `review-findings-full.jsonl` and the code's de-facto derivation (`_derive_code_review_tally` over the composed all-rounds findings).
- **Source**: user

## Decision 2: Fix scope across skills
- **Question**: Fix only /implement Step 5, or also explicitly cover standalone /review?
- **Resolution**: Fix the shared `voting write-tally` writer (structurally corrects both /implement and /review). Add a regression test for the /implement Step 5 multi-round case only. Standalone /review benefits automatically; no separate /review test required.
- **Source**: user

## Decision 3: Historical committed tallies (non-goal)
- **Question**: Should already-committed wrong `code-review-tally.json` files be backfilled / corrected?
- **Resolution**: No. Historical `larch-logs` are immutable run records; backfilling is out of scope. Consumers (`audit-runs`, `/fluff-analysis`, token/cost summaries) that read historical tallies are not modified by this fix.
- **Source**: codebase / orchestrator

## Scope boundaries and hard constraints
- **In-scope**: make the code-review tally write resilient so multi-round runs commit correct cumulative `rounds` / `accepted_count` / `rejected_count`; document the semantics; add a /implement multi-round regression test.
- **Hard constraints**: do NOT change plan-review tally behavior (plan-review STORES the body, so its header validation is meaningful and must stay); preserve the code-review-tally record schema (`schema_version` 2; `phase` / `batch` / `mode` / `rounds` / `accepted_count` / `rejected_count` / `exonerated_count`); keep `review-findings-full.jsonl` behavior unchanged (already correct).
- **Non-goals**: backfilling historical logs; changing tally consumers; expanding the /review test surface; redesigning the flush/commit pipeline.
