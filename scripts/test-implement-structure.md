# test-implement-structure.sh

High-level structural harness for the wrapperized `/implement` prompt. It verifies that the heavy prose moved to references, SKILL.md calls the Step wrapper scripts, wrapper siblings exist, and helper scripts document the current Step 0, Step 5, Step 8, Step 18, telemetry, and launcher responsibilities.

## Launcher invariants

- Five pre-bootstrap call sites retain the old plugin-root guard shape.
- The two Preflight `plan-block read` fences remain guard-only old-shape anchors.
- Post-Step-0 call sites use `bash "$IMPLEMENT_TMPDIR/larch-run.sh" <relative-script>`.
- Background wrapper assertions match the one-line launcher form for Step 5 review, Step 7a, and Step 8.
- Timeout assertions and `<task-notification>` assertions remain load-bearing.
- Wrapper sibling and executable checks still pin every local `skills/implement/scripts/*.sh` helper used by the prompt.

## Caller

`make test-implement-structure` and the Makefile harness shard.
