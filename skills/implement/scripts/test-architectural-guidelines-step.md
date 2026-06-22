# test-architectural-guidelines-step

Thin `/implement` architectural-guidelines helper.

## Purpose

Delegates to `python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" architectural-guidelines ...` for the post-Step 7a guideline staging contract.

## Callers

`skills/implement/SKILL.md` owns the prompt-side sequencing. The Python CLI owns parsing, path checks, staged assessment writes, durable pinning, and invalidation.

## Harness

`skills/implement/scripts/test-architectural-guidelines-step.sh` pins the prompt-side staging prose and staged-to-durable copy behavior.
