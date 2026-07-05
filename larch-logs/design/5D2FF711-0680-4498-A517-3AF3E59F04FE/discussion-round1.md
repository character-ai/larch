## Decision 1: Set 1 regression fix direction (main-agent OOS promotion)
- **Question**: How to fix main-agent OOS being dropped from aggregate-pool promotion in `_promote_aggregate_oos_pool` (python/larch/review/review_tally.py, main-agent branch)?
- **Resolution**: Remove the `artifact_marked_fileable` conjunct from the main-agent branch only. Main-agent OOS is vote-less and fileable by construction, so promote unconditionally (non-security), restoring pre-#6430 behavior. Keep the marker gate on the voted `pool` branch. Add a marker-less main-agent regression test and fix the existing `test_emit_tally_promotes_fileable_main_agent_oos` fixture that hand-adds `Fileable=true`. Do NOT change any prompt/schema (marker-emit alternative explicitly rejected).
- **Source**: user

## Decision 2: OOS_6 count reconciliation (progress report)
- **Question**: How to reconcile recomputed progress-report OOS counts (which overstate filing) with the fileable-only `OOS_ACCEPTED_COUNT`?
- **Resolution**: Split "proposed" vs "fileable". Keep the vote-accepted count relabeled as "proposed" and add a distinct "fileable" count to the operator-facing report so both are visible. Do NOT collapse to a single fileable-only number.
- **Source**: user

## Scope boundaries (in-scope)
- Set 1: fix main-agent OOS promotion regression in `python/larch/review/review_tally.py` + regression test.
- OOS_4: update stale prose in `docs/voting-process.md` — filing statement (add fileable / strict-majority-`major` qualifier) and retire the `blocker` label in the scoring prose (`major` only).
- OOS_6: split proposed vs fileable OOS counts in `python/larch/report/progress_report.py`.
- OOS_3: drop dead `--oos-file` and `--input-mode` args from `prune_nit_findings` (`_parse_prune_args`) in `python/larch/review/review_aggregate.py` and remove the stale `--input-mode plan` flag from the prune caller in `python/larch/review/plan_review_round.py`.

## Out-of-scope (explicit refusals — do NOT reimplement)
- OOS_1, OOS_2, OOS_7, OOS_8: already resolved by #6430. Do not touch.
- Do NOT alter the voted `pool` branch gate in `_promote_aggregate_oos_pool` (the voted branch legitimately keeps `artifact_marked_fileable`).
- Do NOT touch the separate `aggregate_findings` `--input-mode` arg in `review_aggregate.py` — only `prune_nit_findings`'s copy is dead.

## Hard constraints
- Removing `--input-mode` from `prune_nit_findings` requires removing the caller's `--input-mode plan` flag in the same change (argparse would otherwise error on the unrecognized flag).
- Preserve `OOS_ACCEPTED_COUNT` as fileable-only (do not regress #6430).
- Main-agent OOS already files directly via the disposition gate reading `oos-accepted-main-agent.md`; the fix only restores promotion into the `oos-accepted-review.md` sink (count/dedup), so it must not create duplicate GitHub filings.
