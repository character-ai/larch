## Goal
Implement issue #4037: [IMPLEMENTING] [BUG] (URGENT) /implement Step 18 bash fence uses unguarded `plugin-root.env` source; crashes with "No such file" when tmpdir is pre-cleaned\n\n**Symptom.**.

## Implementation Plan
**Symptom.**

When `/implement` runs with `--merge`, Step 18 fails with:

```
/bin/bash: <TMPDIR><id>/plugin-root.env: No such file or directory
```

The error is non-zero exit from the Step 18 bash fence, so the teardown sequence (`step-18-finalize.sh`) is never invoked.

**Root cause (two layers).**

1. **Non-canonical bash fence.** Every Step 18 bash fence in `SKILL.md` should use the canonical guarded source form:
   ```bash
   [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/plugin-root.env" ] && . "$IMPLEMENT_TMPDIR/plugin-root.env"
   ```
   The `[ -f "$IMPLEMENT_TMPDIR/plugin-root.env" ]` test is the load-bearing safety net: when the file is absent, the `&&` chain short-circuits silently and the source is never attempted. In the failing run the orchestrator used the simpler unguarded form:
   ```bash
   IMPLEMENT_TMPDIR=<VALUE> && . "$IMPLEMENT_TMPDIR/plugin-root.env" && export IMPLEMENT_TMPDIR && step-18-finalize.sh
   ```
   Without the `-f` guard, bash attempts the source unconditionally and fails hard when the file is missing.

2. **Condition that exposes the bug.** `implement-finalize.sh teardown` (via `run_teardown()`) calls `session cleanup-tmpdir` at the end of a successful teardown, which removes the entire `$IMPLEMENT_TMPDIR`. If Step 18 ran once and succeeded (deleting the tmpdir), any subsequent re-invocation of the Step 18 fence finds `plugin-root.env` gone. With the guarded form this would be a silent no-op; with the unguarded form it is a crash.

**Impact.** Step 18 teardown silently does not run when the fence crashes early. Downstream effects: tracking-issue rename to `[DONE]` may not fire, timing/token cap marks may be skipped, and the session pointer is not cleared — stale `~/.cache/larch/sessions/` entries accumulate.

**Suggested fix.**

Short-term: enforce the canonical guarded source form at all Step 18 (and all other post-Step-0) bash fence sites in `SKILL.md`. A `scripts/test-implement-fence-shape.sh` structural check (or extension of the existing lint) can pin the required guard syntax so drift is caught in CI.

Structural fix: Issue #4011 and Issue #4018 are related but separate.

**Fix scope:** enforce canonical guarded source form at all Step 18 bash fence sites in `SKILL.md`.

## Test plan
(no test plan section in plan-file)
