## Proposed Design Outline

### Goals
- Fix the #6430 regression that silently drops main-agent OOS from `oos-accepted-review.md` promotion (undercount plus lost pre-file dedup).
- Reconcile operator-facing OOS counts and refresh the stale operator doc left behind by #6430.
- Remove provably-dead `prune_nit_findings` args and their stale caller flag.

### Non-goals
- Do not redo #6430 work (OOS_1, OOS_2, OOS_7, OOS_8) or weaken the voted-pool fileable gate.
- No prompt or schema changes (marker-emit alternative was rejected); no duplicate GitHub OOS filings.
- Do not touch the separate `aggregate_findings` `--input-mode` arg.

### Approach sketch
- Set 1: drop the `artifact_marked_fileable` conjunct from the main-agent branch of `_promote_aggregate_oos_pool`; keep it on the voted `pool` branch. Main-agent OOS is vote-less and fileable by construction.
- OOS_6: in `progress_report.py`, keep the vote-accepted OOS count relabeled as "proposed" and add a distinct "fileable" count so operators see both (fileable derived from vote/severity data or the canonical fileable-only count).
- OOS_4: update `docs/voting-process.md` filing prose to add the fileable / strict-majority-`major` qualifier, and retire the `blocker` label in the scoring prose (`major` only).
- OOS_3: delete `--oos-file` and `--input-mode` from `prune_nit_findings` (`_parse_prune_args`) and drop the caller's `--input-mode plan` in `plan_review_round.py`.

### Surfaces in scope
- `python/larch/review/review_tally.py` and `python/tests/review/test_review_tally.py`
- `python/larch/report/progress_report.py` and its report tests
- `python/larch/review/review_aggregate.py`, `python/larch/review/plan_review_round.py`, and their tests
- `docs/voting-process.md`

### Open questions
- None. Both genuine forks were resolved in Step 1c: remove-the-gate for Set 1; split proposed vs fileable for OOS_6.
