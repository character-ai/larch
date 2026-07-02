## Goal
Implement issue #6024: [IMPLEMENTING] [BUG] #5889 residuals: orphaned reviewer fragment, unbound REVIEW_MODE, skipped telemetry.

## Implementation Plan
## Summary

Three small residuals from #5889 / PR #5999 (availability policy): the conflict-resolution Code Reviewer fragment is now an orphaned generated artifact with stale authority prose; the new self-review-required early return skips round telemetry; and the new /review self-review reference defaults its `--mode` from a REVIEW_MODE variable that is bound nowhere.

## Original report

From the 2026-07-02 post-merge audit of #5889 / PR #5999 at 63ed17f18. Items two and three were flagged in that run as OOS_2 and OOS_1 nits and dropped before the vote; 0 OOS filed. All three verified live at HEAD.

## Reproduction scenario

- (a) Inspect scripts/generators.tsv row 5 and grep for runtime consumers of skills/shared/reviewer-templates-code-reviewer.md: the only consumer (conflict resolution Phase 3d) was removed when #5889 made conflict resolution main-agent-only.
- (b) Drive /implement Step 5 into the new self-review-required branch (both vendors down) and inspect the run log: the failed round's timing rows and review batches are absent.
- (c) Trigger the /review zero-survivor self-review fallback from a description-mode review and read review-round-summary.md: the mode is stamped `diff`.

## Expected behavior

No orphaned generated artifacts or stale authority prose; degraded rounds still record timing and batch telemetry; the self-review reference resolves the actual review mode.

## Observed behavior

- (a) scripts/generators.tsv:5 still generates skills/shared/reviewer-templates-code-reviewer.md, and skills/shared/reviewer-templates.md:5,652 still says the fragment serves conflict resolution. Generate-check passes, so this is drift, not breakage.
- (b) python/larch/review/review_and_fix.py:572-584: the self-review-required early return skips `_record_step5_round_timing_before_gates` and `flush_review_batches` (mirrors the pre-existing MAV early-return shape).
- (c) skills/review/references/self-review.md:27 uses `--mode "${REVIEW_MODE:-diff}"`; REVIEW_MODE is not bound anywhere in the /review skill tree (repo grep finds only this occurrence), so description-mode fallbacks stamp `Mode: diff` into review-round-summary.md and review-summary.json.

## Root cause analysis

(a) The generator row and prose were missed by #5889's replacement-surface sweep. (b) and (c) were consciously deferred as nits during that run's review. Metadata-level defects only; no functional break found.

## Evidence

- Audit reads at 63ed17f18 of generators.tsv, reviewer-templates.md, review_and_fix.py, self-review.md (citations above).
- Run log larch-logs/implement/5BCCC59E-81CA-49EA-806B-0D9B6F1BB701: OOS_1 and OOS_2 dropped as nits; the audit independently re-derived both before reading the run log.

## Affected files

- scripts/generators.tsv, skills/shared/reviewer-templates-code-reviewer.md, skills/shared/reviewer-templates.md.
- python/larch/review/review_and_fix.py.
- skills/review/references/self-review.md.

## Suggested fix(es)

- Remove the generator row, the generated fragment, and the stale prose (or re-point the fragment at a real consumer if one is planned).
- Record round timing and flush review batches before the self-review-required early return.
- Thread the actual mode into the self-review reference (bind REVIEW_MODE at the call site) or replace the variable with explicit per-mode instructions.

## Open questions

- Is the Code Reviewer fragment intended for future reuse by another lane (keep and re-document) or truly dead (delete)?

## Test plan
(no test plan section in plan-file)
