# design-clarify.sh

Thin wrapper for the two-phase `/design` Step 0b clarify helper.

## Purpose

Validates wrapper argv, sources the optional session env, rebuilds
`_delegate_args`, and delegates to `scripts/larch.sh design clarify`. The
Rust entrypoint owns route-state fallback, pause-save termination, fetch,
publish, result env writes, and failure routing.

## Phases

- `--phase fetch --issue N`: verifies `clarify state` is `awaiting-response`,
  fetches the matching request comment in process, writes
  `$DESIGN_TMPDIR/clarify-request.md`, and emits
  `CLARIFY_FETCH_STATUS=ok` plus durable file paths.
- `--phase publish --issue N`: reads `$DESIGN_TMPDIR/clarify-plan.md` and
  `$DESIGN_TMPDIR/clarify-response.md`, redacts and writes the plan block,
  runs design-log publish fail-closed, posts the clarify response, removes the
  clarification label, and renames to `[DESIGNING]` only when `SESSION_ID` is
  non-empty and `PUBLISH_OK=true`.

## Invariants

- Invoked through `design-run-$PPID.sh`, which supplies `--session-env-path`
  and `--claude-pid`.
- Accepts the current issue explicitly through `--issue`.
- The wrapper validates `--phase`, `--issue`, and `--claude-pid` before
  delegating. It does not forward consumed `"$@"`.
- The Rust owner falls back to `.design-step0-route-state.env` for `REPO` when
  the session env lacks it. Missing route state is benign. Present unreadable
  route state emits `route-state-read-failed`; fetch stages `failed-clarify`,
  publish does not.
- Fetch failures emit `SUMMARY_OUTCOME=failed-clarify` with the fetch status.
  `state-read-failed` and `fetch-read-failed` are legacy subprocess-only tokens
  and are not emitted by `scripts/larch.sh design clarify`.
- Never prints request or response bodies on stdout. Bodies move through files.
- Does not emit `--state designed`; clarify-only updates are not terminal
  design completion.

## Harness

Wrapper delegation and argv validation are covered by
`skills/design/scripts/test-design-clarify.sh`. Phase behavior is covered by
the Rust owner's in-crate tests in
`crates/larch-cli/src/clarify_orchestrator/tests.rs`. Structural pins live in
`make test-design-structure`.
