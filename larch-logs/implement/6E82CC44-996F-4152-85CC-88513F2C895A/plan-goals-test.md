## Goal
Implement issue #5032: [IMPLEMENTING] [BUG] Plan-review converged zero-findings round misclassified as panel-failed.

## Implementation Plan
## Summary

A converged plan-review round, where every reviewer reports zero findings, is misclassified as `panel-failed`. When reviewers raise nothing, `findings-in-scope.md` and the ballot are empty, but the round still dispatches the 3-voter panel against that empty ballot. Voting an empty ballot inevitably degrades, and the voter-dispatch gate maps the degraded result to `panel-failed` instead of the benign `zero-findings-degraded-panel`. The result: a clean, fully-converged review is reported to the operator as a review failure.

## Original report

`/design` plan review reports `STEP3_REVIEW_LOOP_STATUS=panel-failed` for a round in which all reviewers correctly found no issues.

Observed in `/design` run `358D3A7D-8FB6-4DC0-AC27-0760A9CB34DC` on issue #4969 (design-log under `larch-logs/design/358D3A7D-8FB6-4DC0-AC27-0760A9CB34DC/`). Rounds 1-4 were productive: 12 findings accepted and applied. By round 5 the plan had converged and all 4 Cursor reviewers emitted `{"no_issues_found": true}`. `findings-in-scope.md` and `ballot.txt` were both 0 bytes, and `AGGREGATOR_STATUS=insufficient-input`. The round was reported as `panel-failed` with `DEGRADED_PANEL_WARNING` "1/3 effective judges produced substantive vote output", which surfaced a degraded-review warning, forced an "acknowledge panel failure" label on Gate C, and printed "panel-failed (5 rounds)" in the run summary.

Reproduced on larch 51.3.4. The plugin cache is byte-identical to repo `main` (`00206410c`) for `python/plan_review_round.py`, `python/plan_review_panel.py`, `python/plan_review.py`, and `python/voting.py`, so this is a current defect in `main`, not one already fixed by recent merges.

## Reproduction scenario

1. Run `/design` on an issue whose plan converges before the review-round cap of 5.
2. Let early rounds accept findings and revise the plan until it stabilizes.
3. In a later round, all reviewers report no findings (empty ballot).

Expected: that round classifies as `complete` or `zero-findings-degraded-panel`. Observed: it classifies as `panel-failed`.

Live evidence: run `358D3A7D-8FB6-4DC0-AC27-0760A9CB34DC`, round 5. A targeted unit reproduction is cheaper than a full `/design`: drive `python/plan_review_round.py:execute_round` (or the round path it calls) with a panel that launches reviewers which all return `{"no_issues_found": true}`, so the composed ballot is empty, and assert the resulting `LOOP_STATUS`.

## Expected behavior

A round in which all reviewers report no findings has an empty ballot and nothing to vote on. It should short-circuit and skip voter dispatch, classifying as `complete` or `zero-findings-degraded-panel`, the same benign treatment the `PANEL_PRUNED_EMPTY` path already gets. The run summary should not report `panel-failed`, Gate C should not demand a "panel failure" acknowledgment, and Gate B should not be bypassed on the grounds of a panel failure.

## Observed behavior

The empty-ballot round is reported as `STEP3_REVIEW_LOOP_STATUS=panel-failed` / `TALLY_PLAN_REVIEW_STATUS=panel-failed` with `DEGRADED_PANEL=1`. The operator sees a degraded-panel warning, a Gate C approval option relabeled to acknowledge panel failure, and "panel-failed (N rounds)" in the final summary, even though the review actually converged cleanly.

## Root cause analysis

In `python/plan_review_round.py`, the empty-ballot (zero-findings) case is not short-circuited before voting, and the inevitable degraded vote is then mapped to `panel-failed`:

1. `_aggregation_ok_for_voting()` (around lines 484-492) returns `True` when the aggregator `REASON` is `insufficient-input`. A zero-findings round therefore passes the aggregation gate (around line 691) instead of short-circuiting.
2. `_compose_attributed_ballot()` reads the empty `findings-in-scope.md` plus empty OOS and writes an empty `ballot.txt` (around line 704). The code then dispatches the 3-voter panel against that empty ballot (around line 722). This is unlike the `PANEL_PRUNED_EMPTY` branch (around lines 595-609), which short-circuits to `zero-findings-degraded-panel` and skips voting.
3. Voting an empty ballot produces no parseable `FINDING_N` votes, so voters degrade or return empty output. The voter-dispatch gate (around line 741, `voter.returncode != 0 or DISPATCH_OK != "true"`) then sets `LOOP_STATUS=panel-failed`. This short-circuits before `_classify_round_loop_status()` (around lines 506-525), which would otherwise return the benign `zero-findings-degraded-panel` for `accepted == 0 and degraded`.

The benign classifier already encodes the intended outcome; it is simply unreachable for the empty-ballot path because the voter-dispatch failure gate fires first.

## Evidence

From run `358D3A7D-8FB6-4DC0-AC27-0760A9CB34DC`, round 5 (`larch-logs/design/358D3A7D-8FB6-4DC0-AC27-0760A9CB34DC/`):

- `plan-review/round-5/cursor-plan-arch-output.txt` (and innovation, pragmatic, requirements) each contain exactly `{"no_issues_found": true}`; each `.tsv` sidecar is 0 bytes. Collector status `ok`, agent `subtype:success`.
- `findings-in-scope.md` and `ballot.txt` are both 0 bytes (written at round-5 time).
- `.step3-review-result.env`: `STEP3_REVIEW_LOOP_STATUS=panel-failed`, `LOOP_STATUS=panel-failed`, `TALLY_PLAN_REVIEW_STATUS=panel-failed`, `AGGREGATOR_STATUS=insufficient-input`, `ACCEPTED_COUNT=0`, `DEGRADED_PANEL=1`, `DEGRADED_PANEL_WARNING=...1/3 effective judges produced substantive vote output.`
- Voter outputs: `claude-vote-output.txt` 865 bytes but dropped from the kept voter paths; `codex-vote-output.txt` 0 bytes with collector `STATUS=EMPTY_OUTPUT` (and an empty retry `codex-vote-output-retry.txt`); `cursor-vote-output.txt` 582 bytes, the lone effective judge. `plan-voter-slots.ndjson.output-files.dropped-slots` records `voter-2 codex collector-failure STATUS=EMPTY_OUTPUT`.
- `review_aggregate.py` (around line 710) emits `reason=insufficient-input` when the aggregator input is empty.
- The final summary "Review Phase Detail" shows rounds 1-4 with 12 accepted findings; round 5 is the empty/degraded one. "Reviewer slot failures: 0".

Contributing factor: Codex returned `EMPTY_OUTPUT (exit code 0)` for both the round-5 Codex-Generic reviewer slot (no output file written) and the Codex voter (even after retry). This is real flakiness, but it is not the primary defect: voting an empty ballot is wrong regardless of Codex, because the reviewers correctly reported zero findings.

## Affected files

- `python/plan_review_round.py` (primary): `_aggregation_ok_for_voting()`, the empty-ballot composition and voter dispatch path, and the line-741 voter-dispatch failure gate that precedes `_classify_round_loop_status()`.
- `python/review_aggregate.py`: emits `insufficient-input` for empty aggregator input.
- `python/plan_review_panel.py`: `voter-dispatch` emits `DISPATCH_OK` / degraded status for the empty-ballot voters.
- `python/voting.py`: `effective_judges()` and the `{effective}/{expected}` degraded warning.
- `python/test_plan_review.py` (and siblings such as `python/test_plan_review_round.py` if present): missing regression coverage for the all-reviewers-report-nothing round.

## Suggested fix(es)

- Detect the empty-ballot / zero-findings case before voter dispatch and short-circuit to `zero-findings-degraded-panel` (or `complete`), skipping voting. Concretely: after composing the ballot in `execute_round`, when the composed ballot has no `FINDING_` or `OOS_` rows (or when `AGGREGATOR_STATUS=insufficient-input` and `findings-in-scope.md` plus OOS are empty), take the same short-circuit branch used by `PANEL_PRUNED_EMPTY` instead of dispatching voters.
- Alternatively, gate the line-741 voter-dispatch failure mapping so an empty ballot does not yield `panel-failed`; route `accepted == 0 and degraded` through `_classify_round_loop_status()` for the benign outcome.
- Add a regression test: a round where all reviewers report no findings (empty ballot) must classify as `zero-findings-degraded-panel` or `complete`, never `panel-failed`.
- Optional follow-up (separate concern): treat Codex `EMPTY_OUTPUT (exit code 0)` as a retryable collector failure for reviewer and voter slots, or document it, so a flaky empty output does not contribute to spurious degradation.

## Related issues (distinct, already fixed)

This is a new variant, not a regression of the recently-fixed collector-stage drops. Phase-2 dedup against the closed cluster confirmed the distinction:

- #4886 (closed; #4885 folded in): the collector dropped a Cursor zero-findings review as `NOT_SUBSTANTIVE` when a narration line preceded the `{"no_issues_found": true}` sentinel. In this run that salvage worked: each Cursor output normalized to the bare sentinel and was collected `OK`. That fix is in place and is not the cause here.
- #4790 (closed; #4789 folded in): `_compose_findings_from_collector` parsed `\x1f`-delimited records while the collector emitted `KEY=VALUE`, so every `STATUS=OK` record was skipped, yielding `COLLECT_OK_COUNT=0`, an empty ballot, and a false `complete`. The fix added the `degraded-empty-collector` classification for `ok_count == 0`. Here `ok_count > 0` (4 Cursor reviewers collected OK), so that path does not apply.

This bug is the next stage. Reviewers are collected OK with `ok_count > 0` and genuinely zero findings, so the ballot is legitimately empty, and the empty-ballot voter dispatch (not the collector) degrades and is mapped to `panel-failed`. The benign `_classify_round_loop_status` zero-findings outcomes (`zero-findings-degraded-panel` for `accepted == 0 and degraded`) are unreachable because the line-741 voter-dispatch gate short-circuits first.

## Open questions

- Should an all-reviewers-report-nothing round map to `complete` (fully clean) or to `zero-findings-degraded-panel` (clean but flagged)? The latter matches the existing `PANEL_PRUNED_EMPTY` short-circuit; the former most accurately reflects "reviewers ran and found nothing".
- Is `_aggregation_ok_for_voting()` returning `True` for `insufficient-input` intended for any non-empty case (for example, raw findings present but aggregation skipped)? If so, the short-circuit should key on the composed ballot being empty rather than on the aggregator reason alone.

## Test plan
(no test plan section in plan-file)
