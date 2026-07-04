## Decision 1: Fix scope — documentation only
- **Question**: Should the fix include code changes (script or hook modifications)?
- **Resolution**: Documentation only. The issue explicitly states "no code change needed for correctness." The v52.4.9 fix (#6268) already handles correctness. The remaining gap is an efficiency issue resolved by clarifying orchestrator behavior.
- **Source**: codebase (issue body)

## Decision 2: Files to update
- **Question**: Which files need to change?
- **Resolution**: `skills/shared/design-background-wait.md` (strengthen fingerprint rule + note expected loop) and `skills/design/SKILL.md` (add or strengthen anti-pattern for repeated non-empty notifications). Hooks confirmed to have `kill -0` PID liveness checks already; no hook changes needed.
- **Source**: codebase

## Decision 3: No-progress guard interaction
- **Question**: Does the no-progress guard need changes or documentation?
- **Resolution**: No changes needed. The guard's recovery message already tells operators how to proceed (increase threshold). The SKILL.md note on spurious notification handling already references #5639. The guard's existing behavior is acceptable.
- **Source**: codebase (hook-no-progress-guard.sh lines 223, 270)
