## Decision 1: Which marker file to check for in-flight detection
- **Question**: Should the fix check `.bg-wait-active` (actual file written by `design_bg_wait_marker_start`) or `.bg-wait-marker-design-step5c` (name used in the issue description)?
- **Resolution**: Check `.bg-wait-active` — that is the actual file written by `design-step5c.sh:design_bg_wait_marker_start`. The issue author used a descriptive name; the real marker is always `.bg-wait-active`.
- **Source**: codebase (`design-step5c.sh` line 91: `_bg_wait_marker="$DESIGN_TMPDIR/.bg-wait-active"`)

## Decision 2: Exit code for in-flight error
- **Question**: Should the scripts exit 0 (soft warning, prelude/cleanup skip) or exit 1 (hard error) for the in-flight case?
- **Resolution**: Exit 1. The issue says "emit a hard error." The Step 6 wrapper (`design-step6.sh`) uses `set -euo pipefail`, so a non-zero exit surfaces visibly to the orchestrator.
- **Source**: issue description ("emit a hard error instead of silently treating it as a failed publish")

## Decision 3: Guard placement
- **Question**: Add the guard only to `design-step6-prelude.sh`, or to both `design-step6-prelude.sh` and `design-step6-cleanup.sh`?
- **Resolution**: Both. The prelude runs first and would prevent cleanup from running on exit 1, but adding the guard to cleanup.sh provides defense in depth if it's ever called independently.
- **Source**: issue description names both; defensive programming

## Decision 4: Test form
- **Question**: Structural checks in `test-design-structure.sh` only, or also a functional test harness?
- **Resolution**: Both. Add `contains` checks for `.bg-wait-active` in `assert_step6_cleanup_wrappers` (structural), plus a new `test-design-step6.sh` functional harness that invokes the scripts with the right filesystem state.
- **Source**: issue description asks for a test that "asserts when … .bg-wait-marker-design-step5c is present, the prelude emits the in-flight error"
