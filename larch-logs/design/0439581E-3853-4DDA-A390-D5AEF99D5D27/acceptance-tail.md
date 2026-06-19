## Acceptance

- The `reviewer-prune-ledger.tsv` header has seven tab-separated columns: `round`, `tool`, `slot`, `label`, `accepted_count`, `rejected_count`, `total_count`; `reviewer_prune_record` writes all seven.
- `reviewer_prune_filter` prunes a combo (rounds 3-4 only, with ≥2 recorded rounds) when, over the last 2 launched rounds, `accepted_sum - rejected_sum <= 0` OR `accepted_sum * 3 < total_sum`. Exactly-1/3 acceptance survives. Round 5 and `LARCH_REVIEWER_PRUNE=off` keep the full panel; malformed/old-schema ledgers fail open.
- Settled `/design` plan-review rounds (`plan_review_round.execute_round`) and zero-finding code-review rounds (`_zero_findings_branch`) append ledger rows, so round 3 filters on live history instead of fail-opening; plan-review record failure is warn-only.
- `docs/point-competition.md` "Conditional spawning" and `docs/configuration-and-permissions.md` `LARCH_REVIEWER_PRUNE` describe the precision-aware rule (net score ≤ 0 or acceptance rate below 1/3; neutral counts only toward the denominator); token allocation stays future work.
- New and updated tests pass: `python/test_review_pipeline.py`, `python/test_plan_review_panel.py`, `python/test_plan_review_round.py`.
- `make py-lint`, `make py-test`, and `make lint` pass.

diff_lines: 275
