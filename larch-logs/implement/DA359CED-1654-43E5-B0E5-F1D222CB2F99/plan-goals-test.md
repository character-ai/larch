## Goal
Implement issue #4811: [IMPLEMENTING] [BUG] plan-review terminal 0-accepted round dropped from Review Phase Detail table.

## Implementation Plan
## Summary

When a `/design` plan-review run stops on a final round that accepts 0 findings, that round's directory has `findings-classification.tsv` but no `round-meta.json`. The Review Phase Detail table only includes round dirs that contain `round-meta.json`, so the terminal round is silently omitted from the table while the run-summary header still counts it. The result is a header vs table round-count mismatch.

## Original report

The plan-review terminal (0-accepted) round writes no `round-meta.json`, so it is dropped from the Review Phase Detail table.

- Run `04E1791D` (issue #4756) completed 4 rounds (header "Plan review: complete (4 rounds)"; result env `FINAL_ROUND_NUM=4`, `ROUNDS_COMPLETED=4`), but the rendered table shows only rounds 1-3. Round 4 (5 suggestions / 0 accepted) is missing because its `round-meta.json` was never written.

## Reproduction scenario

Run `/design` on an issue where the plan-review loop stops on a round that accepts 0 findings (the clean-stop case). Inspect the run-log subtree: the terminal round dir has `findings-classification.tsv` but no `round-meta.json`. The run-summary header reports N rounds while the Review Phase Detail table shows N-1 rows.

Direct evidence: the merged run-log subtree for run `04E1791D` (`larch-logs/design/04E1791D-.../plan-review/round-4/`) contains `findings-classification.tsv` (5 findings, all neutral, 0 accepted) but no `round-meta.json`.

## Expected behavior

Every completed review round (including the terminal 0-accepted stop round) should appear in the Review Phase Detail table, and the table row count should equal the header round count (`rounds_completed` / `FINAL_ROUND_NUM`).

## Observed behavior

The terminal 0-accepted round is dropped from the table because no `round-meta.json` was written for it, even though the round ran a full panel and vote (its `findings-classification.tsv` exists). The header still counts it, so header says N rounds and the table shows N-1.

## Root cause analysis

`python/progress_report.py` `_completed_round_dirs` (line 584) returns only round dirs whose `round-meta.json` is a file. `write_design_round_meta` (around line 1830) is evidently not invoked (or not persisted) for the terminal 0-accepted stop round, so that round dir is excluded from `render_phase_detail` while the header round count still includes it. The exact loop terminal path that should call `write_design_round_meta` for the final round needs confirmation (likely `python/plan_review.py` / `python/plan_review_round.py` exits the round loop before the meta write on the stop decision when 0 findings were accepted).

## Evidence

- Run-log subtree for `04E1791D`: `plan-review/round-4/findings-classification.tsv` present (5 findings, all neutral, 0 accepted); `plan-review/round-4/round-meta.json` absent.
- `python/progress_report.py:584` `_completed_round_dirs` filters on `(p / "round-meta.json").is_file()`.
- Header round count comes from `rounds_completed` / `FINAL_ROUND_NUM`, which counted round 4.
- Healthy runs whose final round accepts >0 (e.g. ending on cap or threshold) do write `round-meta.json` for every round, so their table matches the header; this gap shows up specifically when the run stops on a 0-accepted round.

## Affected files

- `python/progress_report.py` - `_completed_round_dirs` (line 584) requires `round-meta.json`; `write_design_round_meta` (around line 1830) is the writer.
- `python/plan_review.py` / `python/plan_review_round.py` - the plan-review loop terminal path that should persist `round-meta.json` for the final (0-accepted) round before stopping.

## Suggested fix(es)

- Write `round-meta.json` for every completed review round, including the terminal 0-accepted stop round, so `_completed_round_dirs` includes it.
- Or make `_completed_round_dirs` fall back to a round dir that has `findings-classification.tsv` when `round-meta.json` is absent, and synthesize counts from the TSV.
- Reconcile the table round count with the header `rounds_completed`.
- Add a regression test: a run ending on a 0-accepted round shows all rounds in the table and the header round count equals the table row count.

## Open questions

- Is this independent of the plan-review loop non-convergence bug #4808? It surfaced alongside #4808 but is independently reproducible on any run that stops on a 0-accepted final round, so it should be filed standalone (NOT blocked by #4808). It is a separate reporting gap from the Total double-count #4809.
- Should the terminal 0-accepted round always run `write_design_round_meta`, or should `_completed_round_dirs` tolerate a missing meta by reading the TSV? Either fix closes the mismatch.

## Test plan
(no test plan section in plan-file)
