# scripts/test-refresh-anchor.sh — contract

Sibling regression harness for `scripts/refresh-anchor.sh`. Verifies that the wrapper composes `assemble-anchor.sh` + `tracking-issue-write.sh upsert-anchor` correctly, forwards their envelopes, distinguishes assemble-failure (exit 1) from upsert-failure (exit 2), and propagates `--anchor-id` to the upsert delegate.

## Strategy

Real `gh` calls are out of scope for unit tests. The harness builds a per-test sandbox under `mktemp -d` containing copies of `refresh-anchor.sh`, the real `assemble-anchor.sh`, and `anchor-section-markers.sh`, plus a stub `tracking-issue-write.sh` whose body the test specifies inline. `refresh-anchor.sh`'s `SCRIPT_DIR` resolves to the sandbox, so it picks up the stub instead of the real script.

## Cases

1. Happy path — assemble + upsert both succeed; both envelopes appear on stdout in order; default `--output` is created at the sibling-of-sections path.
2. Upsert failure — assemble succeeds, stub emits `FAILED=true` and exits non-zero; wrapper exits 2 and forwards both envelopes.
3. Missing `--sections-dir` — invocation error; wrapper exits 1 with `FAILED=true` + usage message.
4. `--anchor-id` forwarding — verified by capturing the stub's argv to a file and asserting both the flag name and value reach the upsert call.
5. Explicit `--warnings-log` forwarding — when the caller passes `--warnings-log <path>`, the flag and value reach `assemble-anchor.sh`; an unsafe `diagrams.md` fragment produces the placeholder substitution and a `Warnings` entry in the log.
6. `IMPLEMENT_TMPDIR` env-default — when `--warnings-log` is omitted but `IMPLEMENT_TMPDIR` is set and `$IMPLEMENT_TMPDIR/execution-issues.md` is writable, the wrapper auto-derives `--warnings-log` from the env var so existing call sites inherit the forwarding without per-site updates.

## Wiring

Wired into `make test-harnesses-3` (prerequisite of `make lint`). Standalone target: `make test-refresh-anchor`.
