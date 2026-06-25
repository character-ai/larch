# step-architectural-guidelines-read

Thin `/implement` architectural-guidelines helper.

## Purpose

Clears stale Phase A artifacts at entry via `python3 ... architectural-guidelines invalidate` so the orchestrator never needs a bare `rm -f "$IMPLEMENT_TMPDIR/$f"` loop, which triggers Claude Code's dangerous-rm safety check. Then delegates to `python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" architectural-guidelines read` for the post-Step 7a guideline staging contract.

## Callers

`skills/implement/SKILL.md` owns the prompt-side sequencing. The Python CLI owns parsing, path checks, staged assessment writes, durable pinning, and invalidation.

## Harness

`skills/implement/scripts/test-architectural-guidelines-step.sh` pins the prompt-side staging prose and staged-to-durable copy behavior.
