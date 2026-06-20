## Goal
Implement issue #4809: [IMPLEMENTING] [BUG] Review Phase Detail Total double-counts findings recurring across review rounds.

## Implementation Plan
## Summary

The "Review Phase Detail" table in the `/design` (and `/implement`) run summary computes its **Total** row as a naive sum of per-round Suggestions/Accepted. When the same finding recurs across review rounds, the Total counts it once per round, so it overstates the distinct work. The "Top reviewers" list inflates the same way. This is the reporting symptom of the plan-review loop non-convergence bug (#4808); it should be recorded as blocked by it, and the reporting should also be hardened so a future recurrence cannot silently produce misleading totals.

## Original report

The Review Phase Detail Total double-counts findings that recur across rounds.

- Run `34B683D0` (issue #4675): rendered Total **20/20** from five identical 4/4 rounds (really ~4 distinct findings).
- Run `04E1791D` (issue #4756): rendered Total **15/12** from three 5/4 rounds (~4-5 distinct findings).
- "Top reviewers" inflates the same way: a reviewer whose single finding is accepted in 3 rounds shows "— 3".

## Reproduction scenario

Run `/design` (or `/implement`) on an issue where the plan-review loop re-raises and re-accepts the same findings across rounds (the #4808 non-convergence condition). Observe that the run-summary Review Phase Detail Total equals roughly per-round-value times round-count rather than the count of distinct findings, and that Top reviewers shows per-round multiples.

Direct evidence is in committed run logs: `larch-logs/design/<RUN_ID>/plan-review/round-N/round-meta.json` (per-round tally) and `findings-classification.tsv` (per-round reviewer attribution) for the two runs above.

## Expected behavior

The Total should reflect **distinct** findings across the run, not the same finding multiplied by the number of rounds in which it recurred. Top reviewers should count each distinct accepted finding once. At minimum, if a per-round sum is intentionally retained, the column should be labeled so it does not imply a distinct-finding count.

## Observed behavior

`Total = sum of per-round Accepted/Suggestions`. With recurrence, identical per-round rows are summed, so `34B683D0` shows 20/20 (5 x 4/4) and `04E1791D` shows 15/12 (3 x 5/4). Top reviewers shows the recurrence count (e.g. "— 3").

## Root cause analysis

`python/progress_report.py` `render_phase_detail` (around line 793) builds one `_PhaseRound` per round from each round's `round-meta.json` tally, then renders the Total as `sum(row.suggestions for row in phase_rounds)` and `sum(row.accepted ...)` (around lines 842-849). There is no de-duplication of findings that recur across rounds. `_top_reviewers` and `_top_reviewers_from_classification` (around lines 654 and 701) aggregate accepted-finding reviewer attribution across per-round `findings-classification.tsv` with the same per-round multiplication.

The renderer is faithful to per-round data; the inflation is produced upstream by the loop re-accepting the same findings each round (#4808). This is a real reporting-robustness gap regardless: the summary should not silently misrepresent distinct work when recurrence happens.

## Evidence

- Per-round `round-meta.json` for run `04E1791D`: `ACCEPTED_COUNT=4` in each of rounds 1-3 for the SAME findings (identical reviewer attribution in `findings-classification.tsv` across rounds: FINDING_1=Cursor-Arch, FINDING_2=Cursor-Innovation, FINDING_3=Codex-Innovation, FINDING_4=Cursor-Pragmatic).
- Healthy runs taper (example `058F6917`: 6/5 4/4 2/2 5/4 6/2), so their Total is meaningful; the naive-sum assumption breaks only under recurrence.
- Total row construction: `python/progress_report.py:843` (`f"| **Total** | **{sum(row.suggestions for row in phase_rounds)}** | ..."`).

## Affected files

- `python/progress_report.py` - `render_phase_detail` Total row (~lines 842-849); `_top_reviewers` (~654) and `_top_reviewers_from_classification` (~701) accepted-finding attribution. These compute the inflated counts.

## Suggested fix(es)

- Compute the Total (and Top reviewers) over **distinct** findings de-duplicated across rounds (key on location + concern / finding identity), so a finding accepted in N rounds counts once.
- Or relabel the Total column so it does not imply a distinct-finding count (for example "round-applications"), keeping per-round rows as-is.
- Add a regression test where the same finding recurs across N rounds and assert the Total counts it once (and Top reviewers shows 1).

## Open questions

- Should the per-round rows stay as-is (showing re-acceptance per round) while only the Total/Top-reviewers dedupe, or should both be distinct-finding based?
- Dependency: this is the reporting symptom of the plan-review loop non-convergence bug #4808; fixing #4808 removes the inflation in practice, but the reporting hardening here is independently valuable. This issue should be recorded as blocked by #4808.

## Test plan
(no test plan section in plan-file)
