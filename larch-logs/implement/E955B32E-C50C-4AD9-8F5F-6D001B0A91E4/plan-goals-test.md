## Goal
Implement issue #6114: [IMPLEMENTING] [OOS] Add regression test that a rebase with an unchanged feature diff preserves the staged architectural-guidelines note.

## Implementation Plan
## Out-of-Scope Observation

**Surfaced by**: Cursor-Arch (design plan-review panel for issue #6106)
**Phase**: design
**Vote tally**: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted

## Description

No behavioral regression test proves that a rebase with an unchanged feature diff preserves the staged architectural-guidelines note. The `/design` plan for issue #6106 (fix for the dropped architectural-guidelines note on routine `/implement --merge` rebases) relies on monkeypatched helper call-contract tests; wiring-only coverage would not catch a helper that skips `pin_note_from_staged_for_current_head` or passes a pre-rebase SHA. Issue #6106's own open questions asked for this class of test, given the same user-facing "dropped because HEAD drifted" symptom has recurred across 8 prior closed issues (#5754, #5969, #6021, #6034, #6059, #6061, #6062, #6063) before #6106 found a 9th, previously-unaddressed call site.

- **Focus area**: architecture
- **Location**: python/tests/implement/test_ship.py (and the analogous test files for ci_monitor.py / ci_agentic_fix.py once #6106 lands)
- **Severity**: latent

---
*This issue was filed as a manual recovery from a `/design` plan-review OOS finding for issue #6106. The plan-review panel accepted this finding unanimously (3-0) in round 1, but `/design`'s round-to-round OOS-cumulation artifact was reset to empty after a clean round 2, so the normal Step 5b auto-filing pipeline reported no accepted OOS items. Filed by hand from the round-1 vote record instead of being silently dropped.*

## Test plan
(no test plan section in plan-file)
