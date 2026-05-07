# scripts/test-launch-cursor-review.sh — contract

Offline regression harness for `scripts/launch-cursor-review.sh`.

## Purpose

Pins Cursor reviewer launcher behavior that is not covered by the generic
`run-external-agent.sh` wrapper harness: launcher-owned `.done` publication,
Cursor JSON post-processing before public completion, outer-launcher retry
metadata, prompt-file replay, signal-trap behavior, and validation-before-side
effects.

## Primary callers

- `make test-launch-cursor-review`
- `make test-harnesses-2`
- `make lint`

## Invariants

- On normal success, `${OUTPUT}.done` appears only after `${OUTPUT}` contains
  extracted `.result` prose, not the raw Cursor JSON envelope.
- `${OUTPUT}.meta` records `OUTER_LAUNCHER`,
  `OUTER_LAUNCHER_PROMPT_FILE`, and `OUTER_LAUNCHER_WORKDIR` so
  `scripts/collect-agent-results.sh` can replay empty Cursor outputs through
  the outer launcher instead of the inner `cursor agent` command.
- `${OUTPUT}.prompt` stores the original unwrapped prompt byte-for-byte, and
  `--prompt-file` preserves trailing newlines through the max-mode wrapper.
- The launcher EXIT trap promotes an existing `.inner.done` or writes a
  synthetic `99` if the wrapper failed before producing one; abnormal exits may
  leave raw JSON in `${OUTPUT}` because post-processing was interrupted.
- Invalid `--output`, invalid `--timeout`, and mutually exclusive prompt source
  flags fail before launcher sidecar or sentinel files are created.

## Test harness

The harness stubs `cursor` on `PATH`, forces `RUN_EXTERNAL_AGENT_POLL_INTERVAL`
to `0.05`, and uses only local temporary files. It does not require Cursor
authentication or network access.

## Edit-in-sync

Update this harness and contract with any change to
`scripts/launch-cursor-review.sh`'s prompt-source flags, `.meta` enrichment,
sentinel publication order, EXIT-trap semantics, or validation timing. Keep the
Makefile target and `docs/linting.md` harness row in sync when renaming or
moving the test.
