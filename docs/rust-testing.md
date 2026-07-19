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
- `GitRepository::builder` creates an owned repository through installed Git.
  `GitFixture` names the shared unborn, detached, refs, changes, conflict,
  non-UTF-8 path, special-file, attributes and filters, sparse-checkout,
  submodule, linked-worktree, hooks and signing, remotes, and corruption states.
  Select `GitObjectFormat::Sha1` or `GitObjectFormat::Sha256`. Match
  `GitFixtureError::Skip` and print its `FixtureCapability` and reason when the
  host lacks a feature. Never turn a capability skip into an unreported early
  return.

Never call `set_current_dir`, `set_var`, or `remove_var` in a test. Do not use a
shared fixed path, port, clock, response queue, or mutable static. Give each
test its own fixture and let Cargo run it in parallel.

## Git oracle and semantic snapshots

Git fixtures may invoke installed Git as a test oracle. `GitRepository` finds
the executable once, then clears the child environment and supplies an owned
home, temp directory, config, identity, dates, locale, and path. Commands set
only the child working directory. Fixture code must not change the test
process environment or working directory. Product crates must still use the
closed Git interfaces described in `ARCHITECTURE.md`; the fixture API does not
authorize a production arbitrary-argument Git runner.

Repository read differential tests exercise the public `RepositoryRead` port
through `GixRepository`. Compare typed IDs, ref targets, config provenance,
URLs, worktree records, and error classes with parsed Git oracle results. Path
comparisons may normalize filesystem aliases such as macOS `/var` and
`/private/var`, but the adapter result must retain its original path bytes.
For status and change sets, compare staged, unstaged, untracked, ignored, and
unmerged paths plus change kinds, modes, IDs, conflict stages, and flags. Cover
pathspec and case configuration, filters and CRLF, sparse indexes, submodules,
non-UTF-8 paths, symlinks, executable bits, and configured rewrite behavior.
An unsupported semantic must return its typed error instead of dropping data.

Use `SemanticSnapshot::capture` after each implementation runs against its own
equivalent repository. Supply the operation's public result through
`ExecutionSnapshot`. Compare the typed snapshots first. Use
`SemanticSnapshot::render` only for a checked-in review artifact. The
`larch-git-snapshot-v1` format captures:

- exit class and bounded public stdout and stderr;
- object IDs and types, refs, reflogs, index stages and modes, index flags,
  and byte-preserving untracked and ignored paths;
- worktree bytes, modes, symlinks, linked-worktree records, operation-state
  files, relevant config, and hook or helper transcripts;
- an independent `git fsck --full --no-dangling` result.

Each byte field stores at most 1 MiB plus its full length, truncation state,
and deterministic checksum. Each filesystem section stores at most 4,096
entries and records section truncation. Rendered paths and bytes use lowercase
hex. Capture replaces the owned temporary root with `<ROOT>` and redacts
credential-bearing config and URL user information. Do not add normalization
for object IDs, modes, paths, repository state, or other semantic values.

Snapshot reviews must explain every changed semantic field. Update a checked-in
render only after both implementations produce the intended state. Test
success, injected failure, interruption, and corruption separately. A failed
Git probe remains snapshot data so corrupt repositories stay comparable.

Normal Git tests remain offline. Use local repositories for remotes and
submodules. Use fixture scripts for hooks, filters, credential helpers,
askpass, signing programs, and other child tools. Store their bounded
transcripts under `GitRepository::transcript_root`; never use live credentials
or a remote URL that can resolve to a service. Run the named fixture matrix on
macOS and Linux. Capability skips must name the missing feature and host error
in test output.

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
