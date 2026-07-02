## Goal
Implement issue #6021: [IMPLEMENTING] [BUG] #5969 residual: closeout-time guideline pin lacks refresh retry on drift.

## Implementation Plan
## Summary

Ship-time guideline-note pinning gained the staged-assessment refresh retry in #5969 / PR #5997, but the closeout-time best-effort pin still calls `pin_note_from_staged` without the refresh, so the same fingerprint-drift drop that #5969 fixed at ship time persists for stall/closeout-only flows.

## Original report

From the 2026-07-02 post-merge audit of #5969 / PR #5997 at 63ed17f18. The run's own review surfaced this exact gap as OOS_1 and dropped it before the vote; run statistics show 0 OOS filed, so no tracking issue exists.

## Reproduction scenario

1. A run stages an architectural-guidelines assessment, then HEAD drifts (rebase or a CI-fix commit).
2. The run never reaches the ship-time pin (for example it stalls) and closeout runs.
3. `_pin_architectural_guidelines_note_best_effort` calls `pin_note_from_staged`; the pin fails on fingerprint drift; no refresh retry runs; the guideline note is dropped.

## Expected behavior

Closeout-time pinning recovers from fingerprint drift the same way ship-time pinning now does: refresh the staged snapshot against the live diff, then retry the pin, with the same fail-closed guards.

## Observed behavior

python/larch/state/closeout.py:238-244 pins without any refresh retry. Impact is bounded: a ship-pinned durable note survives via the post-merge skip at closeout.py:234-237, so the drop affects only flows that never ship-pinned (stall and closeout-only paths).

## Root cause analysis

The #5969 vetted plan scoped the refresh retry to the ship path (python/larch/implement/ship_guidelines.py caller); the closeout caller was identified during that run's review as the remaining surface of the same bug class and consciously left out of scope. This is a pre-existing gap surfaced by the fix, not a regression introduced by it.

## Evidence

- closeout.py:238-244 (`_pin_architectural_guidelines_note_best_effort`) and closeout.py:234-237 (post-merge skip), verified at 63ed17f18 by the audit.
- Refresh recovery shipped for the ship path: python/larch/core/architectural_guidelines.py:499-514.
- Run log larch-logs/implement/65BA514A-F205-46C1-B569-78F2B42AE88C: OOS_1 text names this call site; run-statistics.md shows "OOS filed: 0".

## Affected files

- python/larch/state/closeout.py: the best-effort pin.
- python/larch/core/architectural_guidelines.py: reuse the existing refresh helper.
- python/tests/core/ and python/tests/state/: add a closeout-path drift test.

## Suggested fix(es)

Call the same refresh-then-retry sequence the ship path uses from the closeout best-effort pin, preserving best-effort semantics (failure still must not block closeout). Add a regression test for pin-after-drift at closeout time.

## Open questions

None identified.

## Test plan
(no test plan section in plan-file)
