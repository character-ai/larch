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
- Specialist `--agent-file ... --mode diff` prompts store the specialist-rendered
  body in `${OUTPUT}.prompt` without the hardening preamble, and replaying that
  sidecar with `--prompt-file` yields exactly one preamble in Cursor argv.
- Model-args preflight failure exits wrapper-level 0 with the five-line
  `LAUNCHER_EXIT` / manifest / QA / transcript / sidecar KV envelope and
  truncates stale `${OUTPUT}.sidecar` bytes before writing diagnostics.
- `${OUTPUT}.dirty-tree` is published before public completion and carries the
  baseline-mode `check-mid-run-dirty-tree.sh` contract; auth-preflight
  short-circuit publishes `STATUS=unknown` with
  `REASON=preflight-short-circuit-no-agent-ran`.
- The launcher EXIT trap promotes an existing `.inner.done` or writes a
  synthetic `99` if the wrapper failed before producing one; abnormal exits may
  leave raw JSON in `${OUTPUT}` because post-processing was interrupted.
- Invalid `--output`, invalid `--timeout` (rejecting both literal `0` and
  zero-padded `00` / `000` via the arithmetic floor check), and mutually
  exclusive prompt source flags fail before launcher sidecar or sentinel files
  are created.
- Stale `${OUTPUT}.json` from a prior run does not leak into the current run's
  `$OUTPUT` or token-ledger record. The launcher clears any pre-existing
  `${OUTPUT}.json` before the `cp`, and on `cp` failure leaves `$OUTPUT` as the
  wrapper-provided bytes (no extraction, no token-ledger update) rather than
  silently consuming a stale prior-run sidecar.
- The post-wrapper test hook is gated: only when `LARCH_ALLOW_TEST_HOOKS=1`
  (exact match) AND `LARCH_TEST_TRAP_AFTER_INNER_DONE_FILE` points at a regular
  non-symlink file does the launcher `source` that file. The legacy
  single-env-var form `LARCH_TEST_TRAP_AFTER_INNER_DONE` (without `_FILE`) is
  not honored regardless of `LARCH_ALLOW_TEST_HOOKS`. Symlinked hook files are
  rejected. Production callers must not set either env var.
- `LARCH_TIMING_TASK_KIND=--prompt` from the environment falls back silently to
  `cursor-review` in the timing TSV, while the CLI `--timing-task-kind` path
  still rejects empty and flag-shaped values with exit 2.

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
