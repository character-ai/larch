## Goal
Implement issue #4996: [IMPLEMENTING] [BUG] /design plan-review aggregator failure forensics overwritten each round.

## Implementation Plan
## Summary

In `/design` Step 3 plan review, the findings aggregator can fail its post-merge validation in an early round and fall back to the un-deduped findings, but its failure forensics are written to **stable per-tmpdir paths** that later successful rounds overwrite. Because the `/design` path runs the aggregator with the top-level `DESIGN_TMPDIR` (not a `round-N` directory), the existing round-stamp logic in `_committed_ref` never fires, and aggregator forensics are never snapshotted into `plan-review/round-N/`. The result: a non-terminal aggregator failure in an early round becomes undiagnosable in the committed run log. The committed `aggregator-validate.stderr` is empty (overwritten by a later successful round) and the `execution-issues.md` "See ... aggregator-validate.stderr" pointer is stale. This is a sibling of #4994 (Cursor structured-output conformance) but distinct: #4994 covers reviewer **slot** TSV row drops and explicitly scopes the aggregator failure out. Cross-reference, do not merge.

## Original report

Observed during design run `FD971172-3DC4-4D78-83F2-4DB57339E873` on issue #4967 (run logs committed via merged PR #4992, under `larch-logs/design/FD971172-3DC4-4D78-83F2-4DB57339E873/`). In round 1 of Step 3 plan review, the findings aggregator failed validation. `execution-issues.md` "External Reviewer Issues" recorded: "**findings aggregator**: merged output failed validation; leaving `findings-in-scope.md` unchanged. See `aggregator-validate.stderr`." The aggregator then left `findings-in-scope.md` at its pre-dedup (un-deduped) state, so round 1 proceeded with un-deduped findings (the run summary shows 14 round-1 suggestions). Rounds 2-5 aggregated fine. Net plan impact was low because of panel redundancy, but that round's dedup/merge was lost and the failure is now undiagnosable: the committed `aggregator-validate.stderr` is empty.

This bug has two facets: (1) a certain, actionable diagnostic-retention defect; and (2) the actual round-1 validator rejection cause, which is unknown precisely because of facet (1).

## Reproduction scenario

The triggering merge failure is a non-deterministic LLM event, so the round-1 rejection cannot be forced on demand. The end-to-end shape: run `/design` on an issue that yields a large round-1 reviewer panel (here 12 reviewers, ~14 raw findings) where the Cursor-dispatched aggregator emits a merge that trips a `_validate_aggregate_output` semantic check (for example, dropping a reviewer slot so "input reviewers missing from merge output" fires), then succeeds in later rounds. Observe that the committed `aggregator-validate.stderr` is empty and `plan-review/round-1/` holds no aggregator artifacts.

The **retention defect itself is deterministically reproducible** at unit level: call `aggregate_findings` twice against the same top-level `--review-tmpdir` (a directory whose name does not start with `round-`). Make the first call fail validation (non-empty `validate_err` written to `aggregator-validate.stderr`) and the second call succeed with no revision-trace warnings (so `_validate_aggregate_output` returns `(0, "")` and `_apply_aggregate_candidate` writes the empty string back to `aggregator-validate.stderr`). After the second call, `aggregator-validate.stderr` is empty: the first failure's evidence is gone, and any `execution-issues.md` pointer written by the first call now resolves to an empty file.

## Expected behavior

A non-terminal aggregator validation failure in any round should leave diagnosable evidence in the committed run log: the exact validator rejection string, the failing merge output, and the round number. The `execution-issues.md` "See ..." pointer should resolve to a non-empty committed artifact even after later rounds succeed. An operator auditing the committed run log should be able to determine why the aggregator failed in round N.

## Observed behavior

The `execution-issues.md` warning fires correctly at failure time, but:
- `aggregator-validate.stderr`, `aggregator-output.txt`, `aggregator-dispatch.env`, and `aggregator-dispatch.stderr` are stable top-level paths overwritten on every round; the committed copies are the last (successful, round-5) state.
- For the `/design` path, `_committed_ref` does not round-stamp the pointer (it only rewrites to `round-N/<file>` when `review_tmpdir.name` starts with `round-`), so the warning points at the bare stable path.
- `plan-review/round-N/` directories contain reviewer forensics but no aggregator artifacts.

Net: the committed `aggregator-validate.stderr` is empty, the pointer is stale, and the round-1 rejection cause is unrecoverable.

## Root cause analysis

**Facet 1 (diagnostic retention; certain, verified against the working tree).** In `aggregate_findings` (`python/review_aggregate.py`), all aggregator forensics are written to stable paths under `review_tmpdir`: `aggregator-output.txt`, `aggregator-slots.ndjson`, `aggregator-dispatch.env`, `aggregator-dispatch.stderr`, and (in `_apply_aggregate_candidate`) `aggregator-validate.stderr` via `_write_text(validate_log, validate_err)`. The Step 3 loop calls the aggregator once per round, so each round overwrites these paths. The `/design` call site (`python/plan_review_round.py`) passes `--review-tmpdir <DESIGN_TMPDIR>` and `--findings-file <DESIGN_TMPDIR>/findings-in-scope.md`; `DESIGN_TMPDIR.name` does not start with `round-`, so `_committed_ref`'s round-stamp branch never fires and nothing snapshots the per-round failure logs. When a later round succeeds, `_validate_aggregate_output` returns `(0, warning_lines)` with `warning_lines == ""` (no revision-trace warnings), and `_apply_aggregate_candidate` writes that empty string back over `aggregator-validate.stderr`. So the committed file is empty, not because the validator produced no detail, but because a later success clobbered the failure detail.

**Facet 2 (the actual round-1 rejection cause; unknown due to facet 1).** The "merged output failed validation" wording is the `aggregate_findings` else-branch warning (`reason=validation-failed`), reached when `_apply_aggregate_candidate` returns rc 2 (a non-OOS semantic rejection from `_validate_aggregate_output`) or an exhausted `_VALIDATION_FAILED_RC` (the OOS-attribution rejection re-dispatched up to `_AGGREGATE_VALIDATION_RETRIES` times, then exhausted). In `--input-mode plan` the per-block Severity-line check is skipped, so the plausible round-1 triggers for a Cursor-dispatched merge collapsing ~14 findings across 12 reviewers are: "input reviewers missing from merge output" (the validator strictly requires every input reviewer slot to reappear in the merge), "unknown reviewer slot in merge output", "block missing reviewer attribution line", "duplicate merged FINDING id", or OOS-attribution exhaustion. The surviving round-5 `aggregator-output.txt` opens with a Cursor prose preamble (`**Aggregator result:** ...`) before the `### FINDING_N:` blocks, consistent with Cursor output-conformance slips, but the round-1 output that actually failed is gone. A secondary consequence: when `validate_err` is empty, the bounded re-dispatch feeds back "(validator produced no detail)" into the retry prompt, weakening self-repair.

## Evidence

- `execution-issues.md` (committed run log, External Reviewer Issues) contains the "findings aggregator: merged output failed validation; leaving findings-in-scope.md unchanged. See ... aggregator-validate.stderr" entry.
- Committed `aggregator-validate.stderr` and `aggregator-dispatch.stderr` are both empty; `aggregator-dispatch.env` shows `ALL_OUTPUT_TOOLS=cursor`, `FALLBACK_COUNT=0`, `DISPATCH_OK=true` (the aggregator ran on Cursor and dispatch succeeded; the failure was purely post-merge semantic validation).
- `plan-review/round-1/` lists reviewer forensics only (`findings-classification.tsv`, `panel-manifest.ndjson`, `reviewer-status.tsv`, `round-meta.json`, `round-summary.env`, `revise/`, the dyn-* reviewer outputs); no `aggregator-*` files.
- `python/review_aggregate.py`: `_validate_aggregate_output` returns a non-empty message string on every non-zero rc; `_apply_aggregate_candidate` writes `validate_err` to the stable `aggregator-validate.stderr`; `_committed_ref` round-stamps only when `review_tmpdir.name` starts with `round-`; `aggregate_findings` writes stable `aggregator-output.txt` / `aggregator-dispatch.{env,stderr}` and is invoked once per round.
- `python/plan_review_round.py` (design plan-review round): invokes `review aggregate-findings` with `--review-tmpdir <DESIGN_TMPDIR>` and `--findings-file <DESIGN_TMPDIR>/findings-in-scope.md`, and writes `findings-in-scope.pre-dedup.md` plus `findings-in-scope.md` immediately before the call, so an aggregation failure leaves `findings-in-scope.md` at the un-deduped state used for voting.
- Run summary for `FD971172`: round 1 = 14 suggestions (un-deduped), consistent with the aggregation fallback; `DEGRADED_PANEL=0` (voting still proceeded).

## Affected files

- `python/review_aggregate.py` — `_validate_aggregate_output`, `_apply_aggregate_candidate`, `aggregate_findings`, `_committed_ref`, `_failure_see_phrase`. Owns the validation, the stable-path writes, the round-stamp logic, and the warning pointer.
- `python/plan_review_round.py` — the `/design` Step 3 aggregator call site that passes `--review-tmpdir <DESIGN_TMPDIR>` (top-level) and the per-round `findings-in-scope*.md` writes. The round number is available here.
- `python/review_pipeline.py` — the `/review` and `/implement` code-review aggregator call site (`review dispatch-panel` flow). Relevant if the fix changes the aggregator contract or where round-stamping happens, to keep both consumers consistent.
- `python/test_review_aggregate.py` — existing aggregator-validate coverage; add a regression that an early-round failure leaves diagnosable committed evidence after a later successful round.

## Suggested fix(es)

1. **(Primary) Preserve aggregator failure evidence per round on the `/design` path.** On any aggregator validation/dispatch failure, snapshot `aggregator-output.txt`, `aggregator-validate.stderr`, and `aggregator-dispatch.{env,stderr}` into `plan-review/round-N/` (consistent with reviewer forensics), or write them to round-stamped filenames, or pass a per-round `review_tmpdir` so the existing `_committed_ref` round-N rewrite fires. The round number is known to the Step 3 loop in `plan_review_round.py`. Add a regression that an early-round failure remains diagnosable after a later success overwrites the stable paths.
2. **(Secondary) Make the `execution-issues.md` "See ..." pointer round-aware for `/design`.** `_committed_ref` currently round-stamps only when `review_tmpdir.name` starts with `round-`; the `/design` warning should point at a durable, round-stamped artifact rather than the clobbered stable path.
3. **(Optional) Guarantee a non-empty, retained validator error.** When `_validate_aggregate_output` rejects, ensure the exact rejection string reaches both the committed log (durably) and the retry-feedback prompt, instead of being clobbered or surfaced as "(validator produced no detail)".

## Open questions

- Should aggregator per-round forensics live under `plan-review/round-N/` (consistent with reviewer forensics) rather than stable top-level paths, for both the `/design` and `/review`+`/implement` consumers?
- Is the strict "every input reviewer slot must reappear in the merge output" rule the most likely round-1 trigger for a large Cursor merge, and if so should that specific rejection be made more salient and durably retained so it can be confirmed next time it fires?
- Should a non-terminal aggregator failure emit a louder, round-stamped run-summary signal (beyond the `execution-issues.md` line) so silent dedup loss is visible during the run, not just on post-hoc audit?

## Test plan
(no test plan section in plan-file)
