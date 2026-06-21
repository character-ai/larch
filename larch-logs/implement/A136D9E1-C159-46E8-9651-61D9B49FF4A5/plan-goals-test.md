## Goal
Implement issue #4890: [IMPLEMENTING] [BUG] /implement code-review pipeline follow-ups (PR #4870): surface degraded panels, reconcile tally denominators, scope aggregator retry.

## Implementation Plan
## Umbrella

Three follow-up bugs in the `/implement` code-review pipeline, all root-caused while analyzing run `5D390C86-BF44-45C4-94A3-33F87DA03A4D` (PR #4870, issue #4868). Combined so the code-review voting / tally / reporting / aggregation surfaces are fixed in one coordinated pass.

- **#4880** — code-review voters silently degrade the panel when a voter's per-item `JUDGE_ERROR` rate stays below the 80% quorum threshold; the per-voter warning is diagnostic-only and never reaches the operator run-summary.
- **#4882** — the run summary shows inconsistent code-review tally denominators ("18 suggestions" vs "0/3 accepted") with no reconciliation between raw-per-finding and canonical-in-scope counts.
- **#4881** — the findings-aggregator validation-retry re-dispatches on *all* semantic validation failures (and appends OOS-specific repair guidance regardless), not only the OOS-attribution case it was meant to recover.

Shared surfaces: `python/review_tally.py`, `python/voting.py`, the run-summary renderer (#4880, #4882); `python/review_aggregate.py` + `python/test_review_aggregate.py` (#4881). The three source issues' full content is preserved verbatim below.

---

## Source: #4880 — [BUG] Code-review voters silently degrade panel when per-voter JUDGE_ERROR stays…

_Originally filed as #4880; preserved verbatim below._

## Summary

In code-review voting, one or more Cursor voters can return `JUDGE_ERROR` for a trailing contiguous block of ballot items, collapsing the effective panel to a single voter for those items. Two guard rails exist but neither caught a real 67%-per-voter failure: the degraded-panel quorum guard only triggers at **≥80%** per-voter `JUDGE_ERROR`, and the per-voter `JUDGE_ERROR` warning is emitted to a diagnostic log only (`log_mode == "log"`), so it never reaches the operator-visible run-summary "Warnings" count. Net effect: 12 of 18 findings in a real run were decided by a single voter's `NO` with no surfaced signal.

## Original report

Observed while analyzing the code-review tally of `/implement` run `5D390C86-BF44-45C4-94A3-33F87DA03A4D` (PR #4870, issue #4868). The final summary reported "Code review: 0/3 accepted" and "18 suggestions". The committed `round-1/findings-classification.tsv` shows that voter-1 (`cursor-validity`) and voter-2 (`cursor-plan-fidelity`) returned real votes for `FINDING_1`–`FINDING_6`, then `JUDGE_ERROR` for `FINDING_7`–`FINDING_18`. Only voter-3 (`cursor-pragmatism`) voted on all 18. So findings 7–18 were rejected on a single 1-`NO` vote with two `JUDGE_ERROR`s, not a 3-judge consensus. The run's surfaced "Warnings: 2" were only the emergency bypasses and the transcript-captured note; no degraded-panel warning appeared.

## Reproduction scenario

Non-deterministic (depends on Cursor voter output). Conditions that reproduce it:

1. Run a code review whose aggregated ballot is long enough that a Cursor voter's output is truncated or otherwise stops emitting `FINDING_N:`/`OOS_N:` `VOTE` lines partway through (here, after ~6 of 18 items).
2. Two of the three voters hit this on the same trailing block, but each voter's `JUDGE_ERROR` rate stays below 80% (12/18 = 67%).
3. Observe: `parse_failed` does not count those voters, no "Degraded code-review panel" warning is written to `voting-tally.md`, the run summary "Warnings" count omits the per-voter `JUDGE_ERROR` notice, and the trailing items are decided by the one remaining voter.

To inspect the exact observed instance, see the committed run log `larch-logs/implement/5D390C86-BF44-45C4-94A3-33F87DA03A4D/round-1/findings-classification.tsv` and `round-1/voting-tally.md`.

## Expected behavior

When two of three voters fail to produce valid votes for a contiguous block of findings, the panel for those findings is effectively degraded (single voter), and that should be (a) detected even below the 80% per-voter threshold, and (b) surfaced in the operator-visible run-summary warnings, not just a diagnostic log. Ideally the underlying truncation that produces the positional `JUDGE_ERROR` block is prevented (chunk long ballots or raise the voter output budget) so trailing findings get a full panel.

## Observed behavior

A 12/18 (67%) per-voter `JUDGE_ERROR` rate stays under the `parse-rate ≥80% JUDGE_ERROR` bar in `review_tally.py`, so those voters are not removed from quorum and no `**⚠ Degraded code-review panel: … parse-rate ≥80% JUDGE_ERROR …**` warning is written. The per-voter `**⚠ Voter <tool>: <n>/<m> ballot items returned JUDGE_ERROR …**` line in `voting.py` is emitted only under `log_mode == "log"` (diagnostic file), so it is not counted in the run-summary "Warnings". The 12 affected findings are rejected on a single voter's vote, silently.

## Root cause analysis

Three contributing factors:

1. **Positional/contiguous `JUDGE_ERROR`** (valid votes for the first ~6 findings, then `JUDGE_ERROR` for the remaining 12) strongly indicates **voter output truncation** on long ballots, not "narrative-only output". The guard's framing ("emitted narrative-only output") does not describe this failure mode.
2. **The `parse_failed` threshold is too lax for partial failures.** A voter that fails 67% of ballot items still counts toward the effective quorum because the bar is `≥80%` per-voter `JUDGE_ERROR`. Two such voters can silently strip 2/3 of the panel on a subset of items.
3. **The per-voter `JUDGE_ERROR` warning is diagnostic-only.** It is emitted via `_plain_diagnostic(...)` guarded by `log_mode == "log"`, so it never reaches the run-summary "Warnings" count that operators read.

Net: in this run no in-scope decision changed (the 3 in-scope findings sat in the clean 1–6 range with full 3-0 panels, and the 12 affected items were out-of-scope nits), so the bug was harmless this time. But a real in-scope finding landing in the truncated tail would be rejected on a single voter with no operator signal.

## Evidence

- `larch-logs/implement/5D390C86-BF44-45C4-94A3-33F87DA03A4D/round-1/findings-classification.tsv` — `v1_vote`/`v2_vote` = `JUDGE_ERROR` for `FINDING_7`..`FINDING_18`; `v3_vote` = `NO`. `FINDING_1`..`FINDING_6` have all three real votes.
- `round-1/voting-tally.md` — `FINDING_7`..`FINDING_18` rows show `YES=0 NO=1 JERR=2`; `FINDING_1`..`FINDING_6` show `NO=3`.
- `final-summary.md` — "Warnings: 2" (emergency bypasses + transcript-captured); no degraded-panel warning.
- `python/review_tally.py` — the `**⚠ Degraded code-review panel: … parse-rate ≥80% JUDGE_ERROR …**` lines gate on `parse_failed`, which uses the ≥80% per-voter threshold.
- `python/voting.py` — the per-voter `**⚠ Voter <tool>: <n>/<m> ballot items returned JUDGE_ERROR …**` is emitted only under `log_mode == "log"`.

## Affected files

- `python/review_tally.py` — `parse_failed` quorum computation and the ≥80% per-voter `JUDGE_ERROR` threshold; the degraded-panel warning text.
- `python/voting.py` — per-voter `JUDGE_ERROR` counting and the `log_mode == "log"`-gated warning emission.
- The Cursor voter dispatch / output handling (the truncation source; confirm the exact module, e.g. the code-voter dispatch path) — needs investigation for why long ballots truncate.
- The run-summary renderer that produces the "Warnings" count (confirm: `python/progress_report.py` / `python/run_logs.py` / `python/final_report.py`) — to surface the per-voter `JUDGE_ERROR` notice.

## Suggested fix(es)

1. **Detect partial-panel degradation per item, not just per voter.** When a finding's effective valid-voter count drops below the panel quorum (e.g. only 1 of 3 voted), flag that finding and/or the round as degraded regardless of the per-voter 80% bar.
2. **Lower or parameterize the per-voter `parse_failed` threshold**, or count contiguous trailing `JUDGE_ERROR` blocks as a distinct "truncated voter" signal.
3. **Surface the per-voter `JUDGE_ERROR` warning to the operator run-summary "Warnings"**, not just the diagnostic log.
4. **Investigate and fix the voter output truncation** on long ballots (chunk the ballot into bounded batches, or raise the voter output token budget) so trailing findings receive a full panel.

## Open questions

- What is the voter output size limit, and does the contiguous `FINDING_7`+ `JUDGE_ERROR` block correspond to a truncation boundary? Re-reading the round-1 `cursor-validity` / `cursor-plan-fidelity` voter output files (if retained) would confirm truncation vs narrative-only.
- Should a finding decided by fewer than the expected number of valid voters be auto-escalated to a main-agent vote rather than rejected on a single vote?
- Is the same gap present in plan-review voting (`plan_review_tally.py`), which shares the `JUDGE_ERROR` taxonomy?


---

## Source: #4881 — [BUG] Findings-aggregator validation-retry re-dispatches on all semantic failures…

_Originally filed as #4881; preserved verbatim below._

## Summary

The bounded validation-retry added for issue #4868 (PR #4870) re-dispatches the findings aggregator on **every** semantic validation failure (`_VALIDATION_FAILED_RC`), not only the OOS-attribution case it was meant to recover. `_validation_retry_prompt` also appends OOS-attribution-specific repair guidance regardless of the actual validator error. As a result, non-OOS structural failures (missing severity, duplicate `FINDING_N` ids, unknown reviewer slots, missing reviewers) burn the full `1 + LARCH_AGGREGATE_VALIDATION_RETRIES` dispatch budget with misleading feedback, and one suggested-repair instruction ("omit that reviewer slot") can conflict with the validator's requirement that every input reviewer appear, risking a second failure before degrade.

## Original report

Raised during the code review of PR #4870 by five reviewers as finding `FINDING_1` ("Retry loop and prompt target wrong failure classes", severity important) and recorded in `larch-logs/implement/5D390C86-BF44-45C4-94A3-33F87DA03A4D/review-findings-full.jsonl` as `REJ_CR1_1`. The 3-judge panel dismissed it 0-`YES`/3-`NO` and it was **not** filed as an out-of-scope follow-up, so the observation would otherwise be lost. This issue captures it as a follow-up to the merged #4868 work.

## Reproduction scenario

1. Configure the aggregator dispatch stub (or a real aggregator) to return a pattern-conforming but semantically-invalid merge that fails validation for a non-OOS reason, e.g. a block missing its `- **Severity**:` line or citing an unknown reviewer slot.
2. Run `python3 python/cli.py review aggregate-findings …` (code or plan mode) with the default `LARCH_AGGREGATE_VALIDATION_RETRIES` (2).
3. Observe: `aggregate_findings` re-dispatches on the non-OOS failure (because `_apply_aggregate_candidate` returns `_VALIDATION_FAILED_RC` for all `validate_rc != 0`), and the retry prompt appended by `_validation_retry_prompt` contains OOS-attribution repair guidance that does not match the actual error. The full retry budget is consumed before degrade.

A focused unit test can assert dispatch count and retry-prompt contents for a non-OOS validation failure.

## Expected behavior

The retry-with-feedback should target the OOS-attribution failure class that #4868 addresses (a non-`[OUT_OF_SCOPE]` block citing an exclusively-OOS reviewer), and the fed-back guidance should match the actual validator error. Non-OOS semantic failures should either degrade single-shot (as before #4868) or retry with **generic** validator feedback rather than OOS-specific instructions.

## Observed behavior

`_apply_aggregate_candidate` returns `_VALIDATION_FAILED_RC` for every `validate_rc != 0` (`review_aggregate.py:574`), and the retry loop re-dispatches on that broad code (`review_aggregate.py:765`). `_validation_retry_prompt` (`review_aggregate.py:621`) always appends the same OOS-attribution repair text regardless of `validator_error`. The real `validate_err` is included too, but the OOS-specific instruction (including "omit that reviewer slot") is unconditional and can suggest a repair that re-fails on the "every input reviewer must appear" check.

## Root cause analysis

Deliberate breadth choice in the #4868 implementation: a single retryable code (`_VALIDATION_FAILED_RC`) is returned for all `_validate_aggregate_output` semantic rejections, and `_validation_retry_prompt` hardcodes OOS-attribution guidance. `_validate_aggregate_output` does not expose a per-rule retriability subcode, so the loop cannot distinguish the OOS-only-reviewer rejection (`review_aggregate.py` ~line 524-525 message: "merged output lacks `[OUT_OF_SCOPE]` while listing reviewer … appears only on OOS-tagged input findings") from other semantic failures. This is a correctness/efficiency refinement, not a regression: pre-#4868, all of these degraded single-shot.

## Evidence

- `python/review_aggregate.py:574` — `return _VALIDATION_FAILED_RC, str(validate_log)` fires for all `validate_rc != 0`.
- `python/review_aggregate.py:765` — `if pipeline_rc == _VALIDATION_FAILED_RC and attempt < max_attempts:` retries on the broad code.
- `python/review_aggregate.py:621` — `_validation_retry_prompt` appends OOS-attribution guidance unconditionally (the "omit that reviewer slot" suggestion can conflict with the missing-reviewers check).
- `larch-logs/implement/5D390C86-BF44-45C4-94A3-33F87DA03A4D/review-findings-full.jsonl` — `REJ_CR1_1` (5 reviewers, important), dismissed without an OOS follow-up.

## Affected files

- `python/review_aggregate.py` — `_apply_aggregate_candidate` (the `_VALIDATION_FAILED_RC` return), the `aggregate_findings` retry loop, and `_validation_retry_prompt`.
- `python/test_review_aggregate.py` — add regression coverage for non-OOS validation failures (assert single-shot or generic-feedback behavior, and dispatch count).

## Suggested fix(es)

1. **Gate the retry on the OOS-attribution failure class** — either match the specific OOS-only-reviewer validator message, or have `_validate_aggregate_output` return an explicit retriability subcode/flag that `_apply_aggregate_candidate` propagates, so only the OOS-attribution rejection re-dispatches and other semantic failures stay single-shot.
2. **Make `_validation_retry_prompt` failure-class-aware** — append OOS-specific guidance only for the OOS-attribution class; for other semantic failures send generic "fix the validator error" feedback with the real `validate_err`.
3. Optionally add an env knob to scope retry to the OOS-attribution class while leaving other semantic failures single-shot.
4. Reconcile the "omit that reviewer slot" suggestion with the "every input reviewer must appear" validator rule so a suggested repair cannot deterministically re-fail.

## Open questions

- Should non-OOS semantic failures retry at all (with generic feedback), or revert to single-shot for everything except OOS-attribution?
- Is a dedicated validator subcode (returned from `_validate_aggregate_output`) preferable to message-string matching for retriability classification?


---

## Source: #4882 — [BUG] /implement run summary shows inconsistent code-review tally denominators…

_Originally filed as #4882; preserved verbatim below._

## Summary

The `/implement` final run summary reports two different denominators for the same code-review round with no reconciliation: the headline shows "Code review: 0/3 accepted" while the Review Phase Detail table shows "18 suggestions" / "0 accepted". Underneath, `round-1/round-meta.json` records `REJECTED_COUNT=18` while `round-1/code-review-tally.json` records `rejected_count=3`, and 8 nit-severity findings were pruned to out-of-scope before scoring (`prune-nit.env`). A reader sees "18 suggestions, 0 accepted" and reasonably concludes 100% of real suggestions were ignored, when the actual split is 3 in-scope findings (all rejected), 13 out-of-scope findings, and 8 nit-pruned.

## Original report

Observed while analyzing `/implement` run `5D390C86-BF44-45C4-94A3-33F87DA03A4D` (PR #4870). The user flagged "18/18 suggestions rejected" as a seeming anomaly. Tracing it showed the "18" and the "0/3" come from different artifacts and different denominators, and no surfaced field reconciles in-scope vs out-of-scope vs nit-pruned.

## Reproduction scenario

1. Run `/implement` on any change where the review panel raises several findings that are mostly nit/out-of-scope (so the canonical in-scope tally and the raw per-finding vote count diverge).
2. Read the final summary: the headline "Code review: X/Y accepted" uses the canonical in-scope tally, while the "Review Phase Detail" table "Suggestions" column uses the raw per-finding vote count.
3. Compare `round-1/round-meta.json` (`REJECTED_COUNT`) against `round-1/code-review-tally.json` (`rejected_count`) — they disagree for the same round.

Observed instance: `code-review-tally.json` = `{accepted_count:0, rejected_count:3}`; `round-meta.json` = `{REJECTED_COUNT:"18"}`; `prune-nit.env` = `PRUNED_COUNT=8, INSCOPE_REMAINING=10`; `review-findings-full.jsonl` = 3 `REJ_CR1_*` + 13 `OOS_CR1_*`.

## Expected behavior

The summary should present reconcilable numbers. Either the table "Suggestions"/"Accepted" denominators match the canonical in-scope tally used in the headline, or the table adds explicit columns/notes that break down raw findings into in-scope vs out-of-scope vs nit-pruned so "18" and "0/3" are obviously the same data viewed two ways.

## Observed behavior

"18 suggestions / 0 accepted" (raw per-finding count) sits directly beside "Code review: 0/3 accepted" (canonical in-scope count) with no explanation of the 3-in-scope / 13-OOS / 8-nit-pruned decomposition. The two backing artifacts (`round-meta.json` `REJECTED_COUNT=18` vs `code-review-tally.json` `rejected_count=3`) disagree, so any downstream consumer that joins them sees an inconsistency.

## Root cause analysis

The run-summary renderer's "Review Phase Detail" table sources its "Suggestions"/"Accepted" columns from the raw per-finding vote count (round-sum, which also counts out-of-scope and nit items that went to the OOS competition), while the headline "Code review: X/Y accepted" sources the canonical in-scope tally (`code-review-tally.json`). `round-meta.json` separately stores the raw `REJECTED_COUNT=18`. No surfaced field decomposes the raw count into in-scope vs OOS vs nit-pruned, so the two numbers look contradictory. This is an observability/reporting defect, not a correctness defect in the review itself.

Related but distinct prior work (both closed/fixed): #4809 ("Review Phase Detail Total double-counts findings recurring across review rounds") addressed multi-round double-counting in the Total row, and #4811 ("plan-review terminal 0-accepted round dropped from Review Phase Detail table") addressed a dropped round. Neither covers the single-round in-scope-vs-OOS-vs-nit denominator mismatch reported here (the "18" vs "0/3" gap within one round, and the `round-meta.json` vs `code-review-tally.json` divergence).

## Evidence

- `larch-logs/implement/5D390C86-BF44-45C4-94A3-33F87DA03A4D/final-summary.md` — headline "Code review: 0/3 accepted"; Review Phase Detail table "18 suggestions".
- `round-1/code-review-tally.json` — `{"accepted_count":0,"rejected_count":3,...}`.
- `round-1/round-meta.json` — `{"tally":{"REJECTED_COUNT":"18",...}}`.
- `round-1/prune-nit.env` — `PRUNED_COUNT=8`, `INSCOPE_REMAINING=10`.
- `review-findings-full.jsonl` — 3 `REJ_CR1_*` (in-scope rejected) + 13 `OOS_CR1_*` (out-of-scope).

## Affected files

- The run-summary renderer that produces the "Review Phase Detail" table and the "Code review: X/Y accepted" line (confirm exact surface: `python/cli.py render run-summary` is the documented entry point; candidates include `python/progress_report.py` and `python/run_logs.py`).
- The tally producers whose denominators diverge: `python/review_tally.py` (writes `round-meta.json` `REJECTED_COUNT`) and the `code-review-tally.json` writer (`python/voting.py` / `python/final_report.py`).

## Suggested fix(es)

1. **Align the table denominators with the canonical tally** — have the "Review Phase Detail" "Suggestions"/"Accepted" columns use the same in-scope count as the headline, or
2. **Add an explicit decomposition** to the table or a footnote: in-scope (voted) vs out-of-scope vs nit-pruned, so "18 raw → 3 in-scope + 13 OOS + (8 nit-pruned)" is legible.
3. Make `round-meta.json` and `code-review-tally.json` agree on, or clearly label, which count is raw-per-finding vs canonical-in-scope, so downstream joins do not see a contradiction.

## Open questions

- Which number should the headline and the table each show by policy: raw per-finding, in-scope-only, or both with labels?
- Are `round-meta.json` `REJECTED_COUNT` and `code-review-tally.json` `rejected_count` consumed by audit tooling (`audit_runs.py`) in a way that depends on the current divergent semantics? Any relabeling must keep those consumers correct.


---

## Test plan
(no test plan section in plan-file)
