# step-architectural-guidelines-prepare

Thin `/implement` architectural-guidelines Phase A helper.

## Purpose

Delegates to `python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" architectural-guidelines prepare` for the combined read-plus-materialize Phase A contract. Python owns invalidation, parsing, path checks, diff snapshot metadata, staged assessment writes, and durable pinning.

## Callers

`skills/implement/SKILL.md` owns the prompt-side sequencing and deviation assessment. The wrapper only resolves `FORKED_TARGET` from `ship-pr-state.sh` then `session-env.sh`, requires `IMPLEMENT_TMPDIR`, and delegates to the Python CLI.

## Exit codes

- `0`: read path succeeded. Guidelines may be absent, invalid, or present with a materialized diff.
- `1`: guidelines were present, but diff materialization failed.
- `2`: invalidation or another hard helper failure occurred before a successful read path completed.

## Harness

`skills/implement/scripts/test-architectural-guidelines-step.sh` pins the prompt-side staging prose, retired wrapper absence, prepare routing, and staged-to-durable copy behavior.
