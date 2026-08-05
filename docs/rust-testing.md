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
- `VendorProcessHarness` installs the Cargo-built fake `claude`, `codex`, and
  `cursor` binaries on a private complete `PATH`. `VendorScript` replays ordered
  stdout and stderr chunks, bounded inter-chunk delays, an exit code, or a
  never-exit process. Recorded contracts load through `VendorContractFixture`.
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
- `RunLogTree::builder` creates isolated run-log staging, cache, pending, and
  object-store doubles. `RunLogFixture` names the historical and durability
  corpora used by reporting parity tests.

Never call `set_current_dir`, `set_var`, or `remove_var` in a test. Do not use a
shared fixed path, port, clock, response queue, or mutable static. Give each
test its own fixture and let Cargo run it in parallel. Cursor config isolation
uses `CursorConfigContext`, which returns a private directory and a
`ChildEnvironment::CursorConfigDir` override for the child request; it must not
mutate `CURSOR_CONFIG_DIR` in the test process.

## Git oracle and semantic snapshots

Git fixtures may invoke installed Git as a test oracle. `GitRepository` finds
the executable once, then clears the child environment and supplies an owned
home, temp directory, config, identity, dates, locale, and path. The path
contains the installed Git directory, the fixture helper directory, and only
the discovered system directories required by Git's shell helpers:
`basename`, `sed`, and `uname`. This keeps Homebrew and `/usr/local` Git
portable without inheriting the full ambient path. Commands set only the child
working directory. Fixture code must not change the test process environment
or working directory. Product crates must still use the closed Git interfaces
described in `ARCHITECTURE.md`; the fixture API does not authorize a production
arbitrary-argument Git runner.

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

The final ownership gate runs in the same cross-platform Rust lane. Focused
coverage is `cargo test --locked --package larch-lint --test git_ownership`.
It injects direct process creation, arbitrary Git arguments, `gix` bypasses,
duplicate owners, a new CLI exception, non-atomic command state, and inventory
drift. The adapter and CLI suites supply the SHA-1/SHA-256, case, path, filter,
hook, credential, worktree, interruption, recovery, and `git fsck` fixtures.

## Run-log fixtures and reporting parity

`larch-test-support` owns offline run-log corpora for the #7683 reporting
migration. `RunLogTree::builder` creates an isolated temporary root with
staging (`larch-logs/<skill>/<run-id>/`), cache, pending-publication, and a
local object-store double. Named `RunLogFixture` values cover absent, partial,
corrupt, checkpoint, interrupted, committed, archive-pending, batch-corpus,
token/timing/progress, credential-bearing transcript, and historical shapes
the tolerant reader still accepts: manifest v1, lifecycle schema v1, and the
legacy panel-prompt-sizes TSV header.

`RunLogSnapshot::capture` builds one bounded semantic snapshot of a run-log
tree: relative paths, modes, byte content or digests, ordering, durability
markers, and the supplied `ExecutionSnapshot`. Capture replaces the temporary
root with `<ROOT>` and redacts credential-bearing lines and URL userinfo.
`ReportSnapshot::capture` records exact machine fields from JSON reports plus
normalized prose from final-summary, final-report, and run-statistics files,
including RFC3339 timestamp substitution.

Use `ReportingParityOracle` to compare two run-log or report snapshots and
report only differing channels. Prefer typed snapshot equality in tests; use
`render` only for checked-in review artifacts (`larch-run-log-snapshot-v1`,
`larch-report-snapshot-v1`). Snapshot reviews must explain every changed
semantic field. Test success, injected failure, interruption, and corruption
separately so those states stay distinguishable.

`LocalObjectStore` is a filesystem double for the documented object-store
operations (`preflight_prefix`, `list`, `upload_create`, `metadata`,
`download`). It stays offline, rejects unsafe keys, and never contacts a
network endpoint. Fixture code must not call `set_current_dir`, `set_var`, or
`remove_var`.

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
executable compatibility boundary. The process adapter may invoke Git. The
parity harness may invoke its documented Python and Rust fixture programs.
`VendorProcessHarness` may invoke its Cargo-built fake vendors. Everything else
uses `FakeProcessRunner`. Real Claude, Codex, Cursor, service credentials, and
remote endpoints belong only in explicit live-smoke runs.
Tests that need vendor process timing use `VendorProcessHarness` with
`TokioProcessRunner`. Never append the ambient `PATH`; a missing fake must fail
with `ProcessErrorKind::Spawn` even when a real vendor executable is installed.

## Coverage and CI

Coverage is CI-only. The `rust-coverage` job installs the pinned tool, enforces
the workspace line baseline, and writes `target/llvm-cov/lcov.info`. Normal
local checks use changed-path Clippy and do not install coverage tooling or
create instrumented artifacts.

The current CI floor is 88.000% lines. It is a no-regression floor, not a
chosen repository target. Raise it when coverage improves. Lower it only with
a documented reason and issue. Coverage excludes
the shared test-support crate, `tests/` and `fixtures/` trees, and build scripts.
Keep that exclusion expression in the CI workflow so the coverage job stays
reproducible.

The Rust suite remains one workspace test lane while it is fast. When it needs
partitioning, shard by Cargo package rather than test-name or source-file
globs. Assign every package to exactly one test shard, keep `--all-features`
and `--locked` on each shard, and retain one unsharded workspace coverage run.
Use recorded CI duration to balance package groups. Keep `rust-gate` as the
stable aggregate check when the internal shard count changes.

`larch test-shard` owns deterministic LPT packing and the literal
single-physical-line `test-harnesses-N:` Makefile grammar. The harness
rebalancer reaches it through `scripts/larch.sh`; any future Rust CI partition
uses the same packer for Cargo package groups. Python pytest collection
sharding remains a separate temporary Python owner until its test surface
leaves the migration.
