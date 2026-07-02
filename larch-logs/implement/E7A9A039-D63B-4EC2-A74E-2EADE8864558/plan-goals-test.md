## Goal
Implement issue #6018: [IMPLEMENTING] [BUG] #5970 residual: done/merged resume reconciliation returns spurious STALLED.

## Implementation Plan
## Summary

`reconcile_committed_stalled_summary_if_recovered` can never succeed when called from the done/merged resume paths in `run_ship`. Resume hydration always installs a terminal merge result, the reconciliation flush then hits the unconditional post-merge refresh skip, and the helper converts an idempotent success into a spurious terminal STALLED. The committed "Outcome: stalled" summary these call sites were added to correct stays uncorrected.

## Original report

From the 2026-07-02 post-merge audit of issue #5970 / PR #6004 at commit 63ed17f18. The audit confirmed the primary #5970 fix layers work (effective-finalize normalization, pre-merge and draft reconciliation, manifest backstop), but found the two call sites added by that run's round-2 accepted review finding ("merged/done resume paths skip reconciliation") are provably inert or harmful: reviewers and the coder missed the post-merge probe interaction. No test covers these two call sites.

## Reproduction scenario

1. An /implement run stalls mid-flight; its run log is committed with heading "Outcome: stalled".
2. The run later recovers: ship completes and the PR merges, but the session dies before postmerge finishes, so ship state resumes as start=done or start=merged while the stalled summary is still committed.
3. Re-invoke `python3 python/cli.py ship pr` for that run.
4. `_resume_done_result` (or the merged branch) calls `reconcile_committed_stalled_summary_if_recovered`; both entry gates pass (committed heading stalled, live outcome recovered).
5. The flush returns skipped with reason `post-merge`; the helper writes terminal STALLED and returns a STALLED ShipResult.

## Expected behavior

On the done/merged resume paths, reconciliation either rewrites the committed stalled summary to the recovered outcome and pushes it, or falls through to the prior behavior: ShipResult OK "already done" on the done path, postmerge continuation on the merged path. A flush skip that is structurally guaranteed on these paths must not be treated as a stall.

## Observed behavior

ShipResult STALLED with detail "run-log reconciliation flush skipped: post-merge". Terminal ship state is rewritten to stalled (`_write_terminal_state`, step `run-log-reconciliation`), replacing the previous OK "already done" outcome. The committed summary is never corrected. State self-heals on the next invocation (PHASE=stalled then fails `_ship_has_active_failure_signal`, so the entry gate returns None), which masks the bug while leaving the reconciliation goal permanently unmet on these paths.

## Root cause analysis

Three interacting pieces, all observed in code at 63ed17f18:

- `_hydrate_resume_context` (python/larch/implement/ship_resume.py:495) sets `merge_result=resume.merge_result`, and resume parsing runs `_valid_merge_result` (python/larch/implement/ship_state.py:166-167), which returns `MERGE_RESULT_DRIVER_ALREADY_MERGED` for any value not already in `POST_MERGE_MERGE_RESULTS`, including empty. The hydrated context on done/merged resume therefore always carries a terminal merge result.
- The flush probe (python/larch/report/run_log_manifest.py:618-619) returns `RefreshSkip(skipped=True, reason=REFRESH_SKIP_POST_MERGE)` whenever `merge_result` is terminal.
- `reconcile_committed_stalled_summary_if_recovered` (python/larch/implement/ship_pr.py:163-178) maps every `refresh.skipped` to terminal STALLED.

Call sites: python/larch/implement/ship.py:263 (`_resume_done_result`) and ship.py:299-306 (resume.start merged branch).

## Evidence

- ship_pr.py:157-178: flush invoked with `ctx.with_(state_file=None)`, then `if refresh.skipped:` writes terminal STALLED with detail "run-log reconciliation flush skipped: {reason}". Verified by direct read.
- run_log_manifest.py:616-619: post-merge sentinel and terminal merge_result both return the post-merge skip unconditionally. Verified by direct read.
- ship_state.py:166-167: `_valid_merge_result` coerces empty to already_merged. Verified by direct read.
- Audit trace: python/tests/implement/test_ship.py covers pre-merge and draft reconciliation but not the two resume call sites.
- Secondary, suspected (LOW): on the draft/no-merge path a retry after a reconciliation push failure can re-render a byte-identical summary; `refresh.skipped` also covers the volatile-only/no-change skip (python/larch/report/run_log_flush.py:519-520), so such a retry would dead-end STALLED without re-attempting the push that would fix origin. Merge-path retries are protected by the idempotent post-ensure flush in ship_merge.py. Likely rare because duration/cost re-render usually changes bytes.

## Affected files

- python/larch/implement/ship.py: the two resume call sites.
- python/larch/implement/ship_pr.py: skip-to-STALLED mapping in `reconcile_committed_stalled_summary_if_recovered`.
- python/larch/implement/ship_resume.py and ship_state.py: merge-result coercion feeding the probe.
- python/larch/report/run_log_manifest.py: unconditional post-merge refresh skip.
- python/tests/implement/test_ship.py: missing coverage.

## Suggested fix(es)

- Distinguish expected skips: on the done/merged resume paths, treat `REFRESH_SKIP_POST_MERGE` as "nothing to reconcile here" and return None, so callers fall through to OK "already done" / postmerge continuation instead of STALLED.
- If reconciliation should genuinely work after merge, route these call sites through a flush entry point that permits post-merge summary rewrite, or rely on the committing-side manifest backstop from the same PR (python/larch/report/final_report.py) and delete the two call sites.
- Add regression tests: stalled committed summary + recovered outcome + resume start done/merged must not produce STALLED and must not rewrite terminal state to stalled.

## Open questions

- Should done/merged-resume reconciliation rewrite the summary at all, or is the committing-side manifest backstop the intended sole owner once merged?
- Is the byte-identical no-change retry path (secondary note) reachable in practice?

## Test plan
(no test plan section in plan-file)
