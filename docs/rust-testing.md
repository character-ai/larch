# Rust Testing

Rust tests must be deterministic, offline by default, and safe under Cargo's
parallel test runner. Use `larch-test-support` from integration tests and from
crate-local tests where the dependency graph permits it.

## Shared fixtures

- `TestWorkspace` owns a temporary root. It rejects absolute paths and dot
  segments, rejects symlink traversal, creates parents, and removes the root
  on drop.
- `TestEnvironment` builds a complete child environment without changing the
  test process. Call `env_clear` before applying its iterator to a command.
- `TestClock` implements the core wall, monotonic, and async clock ports.
  Sleeps advance injected time without waiting.
- `FakeProcessRunner` records typed requests and returns queued outcomes.
  `ProcessOutputBuilder` creates byte-exact success and failure results.
- `HttpResponseBuilder` creates in-memory responses and rejects invalid status
  codes, header names, and header line injection.

Never call `set_current_dir`, `set_var`, or `remove_var` in a test. Do not use a
shared fixed path, port, clock, response queue, or mutable static. Give each
test its own fixture and let Cargo run it in parallel.

## Test boundaries

- Unit tests live in a crate-local `#[cfg(test)]` module. They cover private
  logic through injected ports. Use an owned workspace if filesystem state is
  part of the behavior; never use the ambient working directory.
- Integration tests live directly under a crate's `tests/` directory. They
  cover the public crate boundary and may use owned filesystem fixtures.
- Golden tests compare complete user-facing or wire-format bytes under
  `fixtures/`. Update goldens only for an intentional, reviewed contract
  change. Keep the update switch opt-in and disabled in CI.
- Property tests cover parsers, codecs, path rules, and other broad input
  spaces. Fix the generator seed in failure output and keep shrinking enabled.
  A property test complements named boundary examples; it does not replace
  them.
- Live-smoke tests exercise a real remote service or vendor executable. Mark
  them ignored by default, require an explicit opt-in, and never run them in
  normal pull-request CI.

Normal unit, integration, golden, property, and coverage runs cannot access an
external network. Use injected HTTP responses. A transport adapter test may
bind an ephemeral loopback port when it must exercise socket framing; it cannot
resolve DNS or contact a non-loopback address.

Do not depend on an installed executable unless the test covers an approved
executable compatibility boundary. The process adapter may invoke Git, and the
parity harness may invoke its documented Python and Rust fixture programs.
Everything else uses `FakeProcessRunner`. Real Claude, Codex, Cursor, service
credentials, and remote endpoints belong only in explicit live-smoke runs.

## Coverage and CI

Install the pinned tool with `make rust-coverage-install`. Run
`make rust-coverage` to print the workspace summary, enforce the measured line
baseline, and write `target/llvm-cov/lcov.info`.

The baseline is 87.377% lines. This was the measured unrounded floor when the
policy was introduced. It is a no-regression floor, not a chosen repository
target. Raise it when coverage
improves. Lower it only with a documented reason and issue. Coverage excludes
the shared test-support crate, `tests/` and `fixtures/` trees, and build scripts.
Keep that exclusion expression in the Makefile so local and CI reports match.

The Rust suite remains one workspace test lane while it is fast. When it needs
partitioning, shard by Cargo package rather than test-name or source-file
globs. Assign every package to exactly one test shard, keep `--all-features`
and `--locked` on each shard, and retain one unsharded workspace coverage run.
Use recorded CI duration to balance package groups. Keep `rust-gate` as the
stable aggregate check when the internal shard count changes.
