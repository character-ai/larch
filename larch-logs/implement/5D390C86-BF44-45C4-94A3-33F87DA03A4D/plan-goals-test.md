## Goal
Implement issue #4868: [IMPLEMENTING] [BUG] findings aggregator OOS-attribution validation fails with no retry.

## Implementation Plan
## Summary

The shared findings aggregator (`python/review_aggregate.py`, `review aggregate-findings`) can produce a merged FINDING block that the post-#2491 `oos_only` attribution check in `_validate_aggregate_output` rejects (rc=2), and there is **no retry or self-repair**: the round silently degrades to un-aggregated (un-deduplicated) reviewer findings and surfaces a warning. This is **not** issue #2491 (which fixed the broad `oos_slots` false positive and is closed): the current code already uses the `oos_only = oos_slots - non_oos_input_slots` fix from #2491. The remaining, unaddressed defect is the **no-recovery degradation** on a validation failure, plus a possible narrow residual edge in the `oos_only` rule. Observed live in an `/implement` code-review round; the aggregator is shared, so `/design` plan-review is affected by the same path.

## Original report

"validation failure" — filed from the `/implement --merge --emergency 4848` run (RUN_ID `BB996541-D0D1-4E00-BC6E-AE424916965C`, PR #4866), whose Step 5 round-5 review surfaced the non-fatal warning: `findings aggregator: merged output failed validation; leaving findings.md unchanged`. This issue captures the root cause of that specific warning.

## Reproduction scenario

Non-deterministic (depends on LLM aggregator output). Conditions that trigger it:

1. Run a review whose panel produces findings where at least one reviewer slot appears **only** on `[OUT_OF_SCOPE]`-tagged input findings (i.e., that reviewer raised no in-scope findings) — the `oos_only` set.
2. The LLM aggregator (`agents/orchestrator-aggregator.md`) emits a **non**-OOS merged block that still cites that OOS-only reviewer slot.
3. `_validate_aggregate_output` rejects the merge at `python/review_aggregate.py:524-525` (rc=2), and `aggregate_findings` degrades with no retry.

To inspect the exact observed instance, see the committed run log:
`larch-logs/implement/BB996541-D0D1-4E00-BC6E-AE424916965C/round-5/aggregator-validate.stderr` and `aggregator-dispatch.stderr`.

## Expected behavior

When the aggregator's merged output fails the OOS-attribution validation, the system should attempt a bounded recovery (re-dispatch the aggregator with the specific validation error fed back, or repair the attribution) before degrading. A single non-deterministic LLM slip should not silently lose the dedup/merge for the whole round. If a residual false positive exists in the `oos_only` rule for legitimate cross-scope merges, the rule should also be tightened.

## Observed behavior

A single aggregation attempt that fails `_validate_aggregate_output` with rc=2 immediately degrades: `aggregate_findings` appends the warning and emits `AGGREGATED=false reason=validation-failed` (`python/review_aggregate.py:740-743`), returning exit 0. The round then proceeds on the raw, un-merged reviewer findings. No retry of the aggregator is attempted for the rc=2 (semantic-validation) failure. The exact validator message was:

`merged output lacks [OUT_OF_SCOPE] while listing reviewer 'cursor-specialist-testing-output.txt' that appears only on OOS-tagged input findings`

Note the "appears **only** on OOS-tagged" wording: this is the **post-#2491** message (the `oos_only` set), confirming the #2491 fix is in place and this is a different failure.

## Root cause analysis

Relationship to #2491 (closed, fixed): #2491 reported the OLD `oos_slots` check (reviewers appearing on **any** OOS finding) rejecting non-OOS blocks, a false positive for reviewers with **mixed** OOS + in-scope findings. The fix (`oos_only = oos_slots - non_oos_input_slots`) is already present at `python/review_aggregate.py:506` and only flags **exclusively-OOS** reviewers. This issue is the post-fix residual, dominated by a separate defect:

1. **No recovery on semantic-validation failure (primary, not covered by #2491).** `aggregate_findings` dispatches the aggregator once (`python/review_aggregate.py:691`) and validates once via `_apply_aggregate_candidate` -> `_validate_aggregate_output` (566). The dispatch-waterfall's retry is gated only on the output **pattern** (`--require-result-pattern`, line 685), not on the semantic OOS-attribution check. A pattern-conforming but semantically-invalid merge passes dispatch and then fails validation with rc=2, which (unlike the narrow-trigger rc=1 cases at 727-737) has no retry branch — the round degrades.

2. **Possible narrow residual false positive in `oos_only` (secondary, distinct from #2491).** Even with the #2491 fix, the rule (`524-525`) rejects any non-OOS merged block citing an exclusively-OOS reviewer. If the aggregator legitimately merges an exclusively-OOS reviewer's finding with an in-scope finding from another reviewer into one block (citing both, marked in-scope), the validator still rejects. Whether that is a legitimate merge (OOS and in-scope findings arguably should stay in separate blocks) or an aggregator error is uncertain without re-reading the round-5 aggregator output; #2491's mixed-reviewer false positive is already fixed, so this is a narrower, separate question.

Net effect is the same regardless: the round loses its dedup/merge with no recovery.

## Evidence

- `larch-logs/implement/BB996541-D0D1-4E00-BC6E-AE424916965C/round-5/aggregator-validate.stderr`: `merged output lacks [OUT_OF_SCOPE] while listing reviewer 'cursor-specialist-testing-output.txt' that appears only on OOS-tagged input findings`.
- `python/review_aggregate.py:506` — `oos_only = oos_slots - non_oos_input_slots` (the #2491 fix is present; only exclusively-OOS reviewers are flagged).
- `python/review_aggregate.py:524-525` — the rule that returned rc=2.
- `python/review_aggregate.py:740-743` — the rc!=0/1/`_MOVE_FAILED_RC` else branch: appends `merged output failed validation; leaving findings unchanged`, emits `reason=validation-failed`, returns 0 (soft degrade, **no retry**).
- `python/review_aggregate.py:685` — `--require-result-pattern` gates dispatch retry on output shape only, not semantics.
- `python/review_aggregate.py:727-737` — rc=1 narrow-trigger cases get distinct handling; rc=2 does not.
- Detection wiring already exists: `python/audit_runs.py:540` and `python/run_logs.py:2601` both scan for the literal `merged output failed validation`, confirming this is a recognized, recurring degradation signature.
- Predecessor: #2491 (CLOSED, fixed via `oos_only`) — same validation surface, different (broad mixed-reviewer) false positive.

## Affected files

- `python/review_aggregate.py` — `_validate_aggregate_output` (the `oos_only` rule), `_apply_aggregate_candidate`, and `aggregate_findings` (the no-retry degrade path). Primary fix site.
- `agents/orchestrator-aggregator.md` — aggregator prompt; candidate site to strengthen the OOS-attribution invariant so the LLM stops producing rejectable merges.
- `python/test_review_aggregate.py` (or the aggregate-findings harness) — regression coverage for the retry/repair path and the OOS-only-reviewer merge case.

## Suggested fix(es)

1. **Bounded re-dispatch on rc=2 OOS-attribution failure (primary; not addressed by #2491).** When `_validate_aggregate_output` returns rc=2 for this check, re-run the aggregator once or twice with the validator's error string appended to the prompt ("you cited reviewer X in a non-OOS block, but X only raised OOS findings; tag it [OUT_OF_SCOPE] or drop it"), then degrade only after the retry budget is exhausted. Mirror the existing dispatch retry budget.
2. **Strengthen `agents/orchestrator-aggregator.md`** to state the invariant explicitly: a merged finding that cites a reviewer whose input findings are all `[OUT_OF_SCOPE]` must itself be `[OUT_OF_SCOPE]`; do not promote exclusively-OOS reviewers into in-scope blocks.
3. **Decide whether the `oos_only` rule should allow legitimate cross-scope merges** (an exclusively-OOS reviewer's finding merged with an in-scope finding). If such merges are intended to be disallowed, document it in the aggregator prompt; if allowed, relax `524-525` to skip the check when the block also cites a non-OOS reviewer. This is the narrow residual beyond #2491's mixed-reviewer fix.
4. If no recovery is added, at minimum make the degrade explicit and bounded so audit tooling and operators can distinguish "aggregation skipped, raw findings used" from "findings lost" (findings are not lost today, but the warning text could say so).

## Open questions

- Is the dominant cause the aggregator prompt (LLM promoting an exclusively-OOS reviewer into an in-scope block) or a narrow residual false positive in the `oos_only` rule for legitimate cross-scope merges? Re-reading `round-5/aggregator-output.txt` against the input findings would disambiguate. (#2491's broad mixed-reviewer false positive is already fixed and is not the cause here.)
- Should rc=2 semantic-validation failures get the same retry treatment as the dispatch-waterfall's pattern-gated retries, or is a one-shot degrade acceptable given findings are not lost?
- Does the same failure mode also degrade `/design` plan-review rounds in practice (`input_mode="plan"`), and should the fix cover both modes uniformly?

## Test plan
(no test plan section in plan-file)
