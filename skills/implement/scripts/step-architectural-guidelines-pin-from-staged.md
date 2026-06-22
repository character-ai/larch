# step-architectural-guidelines-pin-from-staged

Thin `/implement` architectural-guidelines helper.

## Purpose

Delegates to `python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" architectural-guidelines pin-note-from-staged` for the Step 16 durable pin contract.

## Callers

`skills/implement/SKILL.md` Step 16 owns the prompt-side sequencing when staged assessment exists but the durable note is missing or unconsumable for current `HEAD`.

## Harness

`scripts/test-implement-fence-shape.sh` pins the one-line launcher fence. `skills/implement/scripts/test-architectural-guidelines-step.sh` covers staged-to-durable copy behavior.
