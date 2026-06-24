## Goal
Implement issue #5334: [IMPLEMENTING] [BUG] Stale under-quorum JUDGE_ERROR warning persists after successful degraded-panel retry.

## Implementation Plan
## Summary

When a code-review round 1 panel is detected as degraded and retried with a fresh panel, the
`under_quorum_items` warning written to `execution-issues.md` during the initial (failed) tally
is not retracted after a successful retry. The stale JUDGE_ERROR warning persists in the final
run summary as a false positive, misleading operators into thinking findings were decided below
quorum in the final panel result.

## Original report

```
code-review panel (round 1): 7 finding(s) decided below the 2-of-3 panel quorum due to per-item
JUDGE_ERROR (FINDING_6, FINDING_7, FINDING_8, FINDING_9, FINDING_10, FINDING_11, FINDING_12);
resolve...
```

## Reproduction scenario

1. Run `/implement` on any issue.
2. During Step 5 code review, have round 1 produce a degraded panel (the `voting-tally.md`
   contains the "⚠ Degraded code-review panel" banner and `under_quorum_items` is non-empty).
3. `review_and_fix.py` detects the degraded round and retries with a fresh panel.
4. The retry succeeds cleanly (no JERR in the final tally).
5. The final run summary still shows the `under_quorum_items` warning from the failed attempt.

## Expected behavior

When a degraded round 1 is retried and the retry is successful (clean tally with JERR=0),
no `under_quorum_items` warning should appear in the final `execution-issues.md` or
operator-visible run summary. The warning should only be surfaced when the panel's
final committed state actually has findings decided below quorum.

## Observed behavior

The final run summary shows:

```
Warnings (2):
  1. Step implement-bootstrap emergency-bypass-log — /implement --emergency preflight bypassed
  2. code-review panel (round 1): 7 finding(s) decided below the 2-of-3 panel quorum due to
     per-item JUDGE_ERROR (FINDING_6, FINDING_7, FINDING_8, FINDING_9, FINDING_10,
     FINDING_11, FINDING_12); resolved by the remaining voter(s).
```

The final `voting-tally.md` for round 1 (after the successful retry) shows JERR=0 for all
findings — the retried panel was clean. The `execution-issues.ndjson` body still contains
the stale JUDGE_ERROR warning from the initial degraded attempt.

## Root cause analysis

The flow is:

1. `review_core_capture()` is called (first attempt). Inside it, `tally-code-votes`
   (`review_tally.py`) runs, finds `under_quorum_items`, and immediately calls `_surface_warning()`
   to write the warning to `execution-issues.md`. `voting-tally.md` is written with
   the "⚠ Degraded code-review panel" banner.

2. Back in `_implement_round_body()` (line ~2420 of `review_and_fix.py`), the check
   `"⚠ Degraded code-review panel" in voting_tally_file` fires. The code retries via a
   second `review_core_capture()` call, which overwrites `voting-tally.md` with clean results.

3. The retry is successful (`degraded_this_round = False` at line 2445). The final
   `voting-tally.md` is clean (JERR=0 throughout).

4. **The stale `_surface_warning` entry in `execution-issues.md` from step 1 is never
   retracted.** `execution-issues.md` is append-only; the retry path does nothing to
   neutralize the warning already written during the failed first attempt.

The `_surface_warning` call inside `review_tally.py` is too early: it writes to the durable
`execution-issues.md` log before the retry decision in `review_and_fix.py` has been made.
`review_tally.py` already emits `UNDER_QUORUM_COUNT=` as a KV output (line 915), so the
caller has the data needed to surface the warning at the right time.

## Evidence

- `larch-logs/implement/4E881491-D15E-4BAB-A693-4E911C820E1F/execution-issues.ndjson` — contains
  the `under_quorum_items` warning for round 1 with FINDING_6–FINDING_12.
- `larch-logs/implement/4E881491-D15E-4BAB-A693-4E911C820E1F/round-1/voting-tally.md` — final
  (post-retry) tally shows JERR=0 for all items; FINDING_6–FINDING_8 rejected with NO=3/JERR=0.
  No "⚠ Degraded code-review panel" banner in this file.
- `python/review_tally.py` lines 879–885: `_surface_warning()` called unconditionally when
  `under_quorum_items` is non-empty, regardless of whether the round will be retried.
- `python/review_and_fix.py` lines 2420–2445: degraded-retry detection fires AFTER
  `review_core_capture()` returns (which includes the tally and warning write).
- `python/review_tally.py` line 915: `UNDER_QUORUM_COUNT` already emitted as KV output —
  caller has data to surface warning post-retry.

## Affected files

- `python/review_tally.py` — contains the premature `_surface_warning` call for `under_quorum_items`.
- `python/review_and_fix.py` — contains the degraded-retry detection and retry loop; the right
  place to surface the `under_quorum_items` warning after confirming no retry is needed.
- `python/test_review_tally.py` — regression harness; likely needs a test for the
  no-spurious-warning-after-retry case.

## Suggested fix(es)

**Preferred approach** — defer `_surface_warning` to the caller:

1. Remove the `_surface_warning` call for `under_quorum_items` from `review_tally.py`'s
   `tally_code_votes_main`. The tally already emits `UNDER_QUORUM_COUNT` and (implicitly)
   `UNDER_QUORUM_ITEMS` data via KV output; the `voting-tally.md` panel-level banner is
   already written there and is sufficient for the round artifact.

2. In `_implement_round_body()` (or its equivalent call site in `review_and_fix.py`), read
   `UNDER_QUORUM_COUNT` from the final `core` env after the retry decision is settled. Only
   call `_surface_warning()` with the `under_quorum_items` message when `degraded_this_round`
   is `False` (or the retry attempt produced the same UNDER_QUORUM_COUNT on a clean tally).

**Alternative** — retract on successful retry:
Append a "previous warning retracted" note to `execution-issues.md` when the retry succeeds
and the retried tally is clean. This is less clean because `execution-issues.md` is append-only
and the retraction note would still show as a "Warning" unless the flush/render step
filters out retracted entries.

## Open questions

- Should the `under_quorum_items` panel-level banner in `voting-tally.md` also be suppressed
  on the retry path, or retained as a round-level diagnostic even when the retry succeeds?
- Does `UNDER_QUORUM_ITEMS` need to be added as an explicit KV output from `tally-code-votes`
  to make the caller-side warning text reconstruction deterministic, or is `UNDER_QUORUM_COUNT`
  sufficient (with the caller re-reading the tally for item ids)?

## Test plan
(no test plan section in plan-file)
