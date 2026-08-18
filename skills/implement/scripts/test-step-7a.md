# test-step-7a.sh

Delegation smoke for `skills/implement/scripts/step-7a.sh`.

## Cases

The smoke tests only the wrapper contract:

1. Repository-root fallback when `CLAUDE_PLUGIN_ROOT` is unset.
2. Explicit `CLAUDE_PLUGIN_ROOT` selection.
3. Exact `scripts/larch.sh implement step-7a` routing and argument forwarding.
4. Stdout, stderr, and exit-status passthrough.

## Behavioral authority

`crates/larch-cli/src/implement_review_commands.rs` owns Step 7a behavior. It covers orchestration order, Code Flow generation and rejection/failure cleanup, diagram upsert gating, fork target selection, rebase exit propagation, the execution-issues checkpoint, terminal KVs, bgjob transport, and argument failures. Black-box parity coverage lives in `crates/larch-cli/tests/implement_review_parity.rs`. Shared diagrams-comment merge behavior is covered by `python/tests/rendering/test_rendering.py`.

## Assertion parity

| Concern | Current coverage |
| --- | --- |
| bgjob-launch relays the started envelope | `step7a_bgjob_launch_relays_started_envelope` |
| Argv failure emits the 7-key bail envelope (exit 2) | `step7a_unknown_flag_emits_argv_bail_envelope` |
| Missing `IMPLEMENT_TMPDIR` bails before work | `step7a_missing_tmpdir_bails_before_work` |
| Architecture preservation and legacy diagram markers | `python/tests/rendering/test_rendering.py` diagrams-upsert tests |
| Wrapper root selection, routing, argv, streams, and exit status | this smoke |

Run `make test-step-7a` for the smoke and `cargo test --package larch-cli --test implement_review_parity` for the Rust parity lane. Run `make agent-lint` and ShellCheck for the retained Bash smoke.

## Invariants

The smoke is Bash 3.2-compatible and uses a fake plugin CLI, so it never exercises Step 7a behavior through the wrapper.
