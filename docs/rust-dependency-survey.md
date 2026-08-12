# Rust Dependency Survey

Issue #7602 establishes the Rust workspace before larch runtime migration.
The survey checked current crates.io metadata, repository activity, and license
metadata on 2026-07-17. All candidates below were active and unarchived.

| Need | Candidates | Maintenance and license check | Selection |
|------|------------|-------------------------------|-----------|
| CLI parsing | [`clap` 4.6.2](https://crates.io/crates/clap/4.6.2), [`bpaf` 0.9.26](https://crates.io/crates/bpaf/0.9.26) | Repositories active 2026-07-17 and 2026-07-15. Both are unarchived and MIT OR Apache-2.0. | Use `clap`. It supplies derive-based parsing and stable help/version output. `bpaf`'s combinator model adds no benefit for the planned subcommand CLI. |
| Serialization | [`serde` 1.0.228](https://crates.io/crates/serde/1.0.228), [`simd-json` 0.17.3](https://crates.io/crates/simd-json/0.17.3) | Repositories active 2026-07-11 and 2026-07-14. Both are unarchived and MIT OR Apache-2.0. | Reserve `serde` for typed wire data, but do not add it until a wire format exists. `simd-json`'s mutable-buffer and performance focus do not fit small lint metadata. |
| CLI assertions | [`assert_cmd` 2.2.2](https://crates.io/crates/assert_cmd/2.2.2) with [`predicates` 3.1.4](https://crates.io/crates/predicates/3.1.4), [`trycmd` 1.2.0](https://crates.io/crates/trycmd/1.2.0) | Repositories active 2026-07-16, 2026-07-09, and 2026-07-09. All are unarchived and MIT OR Apache-2.0. | Use `assert_cmd`, `predicates`, and `tempfile` for F2's CLI fixture harness. F1 uses Clap's built-in validator. `trycmd` snapshots would make small diagnostic changes costly. |
| Repository-relative path selection | [`globset` 0.4.19](https://crates.io/crates/globset/0.4.19), [`ignore` 0.4.30](https://crates.io/crates/ignore), [`walkdir` 2.5.0](https://crates.io/crates/walkdir) | Repositories are active and unarchived on 2026-07-17. `globset` and `ignore` are Unlicense OR MIT; `walkdir` is Unlicense OR MIT. | Use `globset` behind the runner's `PathSelector` adapter. Do not use a filesystem walker or `ignore`: a walker can include untracked files, and ignore rules cannot authoritatively reconstruct Git index membership. |
| Repository root and tracked-file discovery | [`gix-discover` 0.53.0](https://crates.io/crates/gix-discover), [`gix` 0.83.0](https://crates.io/crates/gix), Git's built-in `rev-parse` and `ls-files` | Gitoxide is active and unarchived on 2026-07-17; its crates are MIT OR Apache-2.0. | Use a narrow `GitCli` adapter for `git -C <cwd> rev-parse --show-toplevel` and `git -C <root> ls-files --cached -z`. The commands are the repository's authoritative, byte-preserving index view. Adding Gitoxide before a rule needs object or index APIs would add a broad dependency without improving this contract. Tool errors, malformed NUL streams, unsafe paths, non-UTF-8 paths, and tracked symlinks fail closed. |
| Cargo integration | [`cargo_metadata` 0.23.1](https://crates.io/crates/cargo_metadata/0.23.1), [`guppy` 0.17.26](https://crates.io/crates/guppy/0.17.26) | Repositories active 2026-04-10 and 2026-06-04. Both are unarchived. `cargo_metadata` is MIT; `guppy` is MIT OR Apache-2.0. | Reserve `cargo_metadata` for direct Cargo graph access, but do not add it before a rule needs Cargo data. `guppy`'s graph analysis is broader than the planned workspace queries. |
| Dependency policy | [`cargo-deny` 0.20.2](https://crates.io/crates/cargo-deny/0.20.2) | Repository active 2026-07-09, unarchived, and MIT OR Apache-2.0. | Use `cargo-deny`. One gate covers advisories, licenses, duplicate versions, wildcard requirements, and untrusted sources. |

The selected runtime dependencies are `clap` and `globset`. The F2 test harness
uses `assert_cmd`, `predicates`, and `tempfile`. Deferred selections stay out of
`Cargo.lock` until code uses them. This keeps the foundation minimal and makes
future dependency additions explicit review points.

## Process-birth identity (issue #8400)

The survey rechecked the Darwin process-information surface on 2026-08-11.

| Need | Candidates | Maintenance, license, and fit check | Selection |
|------|------------|-------------------------------------|-----------|
| Darwin process-birth identity stable across `exec` | [`libproc` 0.14.11](https://crates.io/crates/libproc/0.14.11), handwritten `proc_pidinfo` FFI, `ps -o lstart` | `libproc` is maintained, MIT licensed, and exposes the Darwin `proc_bsdinfo` creation seconds and microseconds through a safe Rust API. Handwritten FFI would violate the workspace `unsafe_code` prohibition. `ps` supplies only a second-resolution display timestamp, so it cannot distinguish same-second PID reuse. | Add target-specific `libproc` only to `larch-adapters`. Use `BSDInfo` creation time on Darwin. Linux needs no new crate: its kernel boot UUID plus `/proc/<pid>/stat` start ticks provides the equivalent durable identity. Its build-only bindgen graph retains `itertools` 0.13 and `shlex` 1, so `deny.toml` names those exact reviewed duplicate exceptions. |

## S3-compatible object storage (issue #8077)

The survey rechecked object-storage metadata on 2026-08-05. The official
`aws-sdk-s3` 1.140.0, `aws-config` 1.10.1, `aws-runtime` 1.9.1, and
`aws-smithy-runtime-api` 1.14.0 crates are Apache-2.0, maintained by the AWS SDK
and Smithy teams, and match larch's Rust 1.94.1 toolchain. The direct
`aws-runtime` edge supplies the non-deprecated in-memory profile-file types used
to remove process and endpoint overrides. The test-only direct Smithy runtime
edge supplies the HTTP connector traits used by larch's small offline test
connector, so SDK request, response, and error mapping can be exercised without
network access or the Smithy protocol-test dependency graph. The runtime
dependencies replace the temporary AWS CLI transport for Rust-owned S3 and R2
lifecycle operations. Default features are disabled: larch enables the Tokio
runtime, the current rustls AWS-LC HTTPS client, and in-process SSO support, but
not `credential_process`. This keeps credentials inside the reviewed adapter
and prevents profile data from introducing a child process.

The SDK's generated S3 graph carries both `http` 0.2 and 1.x request models and
the digest 0.11 family. `deny.toml` retains the global duplicate deny and names
only the independently required older `http` 0.2.12, `http-body` 0.4.6,
`const-oid` 0.9.6, and `sha1` 0.10.7 generations. `cargo deny --all-features`
passes with no advisory, license, or source exception.

## Async runtime (issue #7659)

The survey rechecked runtime metadata on 2026-07-18.

| Need | Candidates | Maintenance, license, and fit check | Selection |
|------|------------|-------------------------------------|-----------|
| Async runtime | [`tokio` 1.53.0](https://crates.io/crates/tokio/1.53.0), [`smol` 2.0.2](https://crates.io/crates/smol/2.0.2), [`async-std` 1.13.2](https://crates.io/crates/async-std/1.13.2) | All are MIT or MIT OR Apache-2.0 and support larch's MSRV. `async-std` is deprecated in favor of `smol`. `smol` remains maintained but needs separate process, signal, cancellation, and task-tracking choices. | Use Tokio with narrow macro, runtime, signal, synchronization, test-time, and time features. One integrated executor and driver set gives larch one ownership model. |
| Cancellation | [`tokio-util` 0.7.18](https://crates.io/crates/tokio-util/0.7.18), task abortion alone, custom token | `tokio-util` is maintained with Tokio, MIT licensed, and provides hierarchical cancellation. Task abortion skips cooperative cleanup. A custom token would duplicate wake and hierarchy behavior. | Use `tokio-util::sync::CancellationToken` behind larch's `Cancellation` type. |

See [rust-async-runtime.md](rust-async-runtime.md) for the execution contract and
rejected alternatives.

## Shared rule foundation (issue #7604)

Issue #7604 establishes the extension points used by every remaining Rust lint.
The survey checked current crates.io metadata, repository activity, and license
metadata on 2026-07-17. All selected crates are active, unarchived, and
license-compatible with larch's MIT license.

| Need | Candidates | Maintenance and license check | Selection |
|------|------------|-------------------------------|-----------|
| Decentralized registration | [`inventory` 0.3.24](https://crates.io/crates/inventory/0.3.24), [`linkme` 0.3](https://crates.io/crates/linkme/0.3) | Both are maintained by dtolnay and MIT OR Apache-2.0. | Use `inventory`. Its typed, distributed registration lets each rule submit metadata and an implementation without editing a central registry. The runner sorts by rule name, so inventory's unspecified iteration order never reaches output. |
| Module discovery | [`automod` 1.0.17](https://crates.io/crates/automod/1.0.17), manual `mod` declarations | `automod` is maintained by dtolnay and MIT OR Apache-2.0. | Use `automod` for `src/rules/`. A new leaf adds its own co-located rule source without changing `lib.rs` or a shared module list. |
| Rust syntax | [`syn` 2.0.119](https://crates.io/crates/syn/2.0.119), [`ra_ap_syntax`](https://crates.io/crates/ra_ap_syntax) | Both are maintained and license-compatible; `syn` is MIT OR Apache-2.0. | Use `syn` with full parsing and visiting. It has the small stable AST surface required by the rule set; rust-analyzer internals would add substantially more churn. |
| Markdown structure | [`pulldown-cmark` 0.13.4](https://crates.io/crates/pulldown-cmark/0.13.4), [`comrak`](https://crates.io/crates/comrak) | Both are maintained and MIT licensed. | Use `pulldown-cmark` for CommonMark events. The shared line iterator deliberately supplements it with fence state because line-oriented lint diagnostics need source-line membership, which event streams do not expose directly. |
| Metadata and migration records | [`serde` 1.0.228](https://crates.io/crates/serde/1.0.228) with [`toml` 1.1.3](https://crates.io/crates/toml/1.1.3), handwritten parser | Both are maintained and MIT OR Apache-2.0. | Use `toml` for strict per-rule migration records. The one-file-per-rule directory rejects missing, duplicate, malformed, and stale records. |
| Text, tabular, and identity helpers | [`regex` 1.13.1](https://crates.io/crates/regex/1.13.1), [`csv` 1.4.0](https://crates.io/crates/csv/1.4.0), [`uuid` 1.24.0](https://crates.io/crates/uuid/1.24.0) | All are maintained and permissively licensed (MIT OR Apache-2.0, Unlicense/MIT, and Apache-2.0 OR MIT respectively). | Establish these shared dependencies now for the filed textual-policy, TSV, and run-id leaves. Their rules remain the sole owners of policy semantics. |
| Shell syntax | [`tree-sitter-bash` 0.25.1](https://crates.io/crates/tree-sitter-bash/0.25.1) with [`tree-sitter`](https://crates.io/crates/tree-sitter), `brush-parser` | Both candidates are maintained and MIT licensed. | Reserve the maintained tree-sitter grammar for the shell-contract leaves. The leaves must still test their required Bash semantics before adopting it; no regex-only parser is introduced by the foundation. |
| Cargo workspace facts | [`cargo_metadata` 0.23.1](https://crates.io/crates/cargo_metadata/0.23.1), [`guppy`](https://crates.io/crates/guppy) | Both are maintained and license-compatible; `cargo_metadata` is MIT. | Establish `cargo_metadata` for the package-architecture leaf. It exposes Cargo's structured workspace view without guppy's larger graph-analysis surface. |

The F3 workspace dependency set is intentionally complete for the already
filed leaves. A leaf may not add a root dependency: a newly discovered shared
need requires a blocked foundation issue and an amended dependency graph.

## Shell contract rules (issue #7610)

The two shell-contract ports evaluate `tree-sitter-bash` and `brush-parser`.
Both are maintained and MIT licensed. The workspace already reserves the
tree-sitter grammar for these leaves, so the port uses it without adding a
dependency. It recognizes Bash commands, redirections, comments, and heredoc
bodies. The only source-line checks left are the established exact preamble
literal and the existing reason-bearing suppression grammar. Those checks are
bounded compatibility rules, not a second shell parser.

## Control-flow analysis (issue #7623)

Before adding the Rust `unreachable-branch` rule, the maintained compiler and
Clippy surfaces were evaluated on 2026-07-17. `rustc`'s `unreachable_code`
lint reports general control-flow unreachable code, while Clippy is a broad
collection of correctness and style lints. Neither provides larch's exact,
deliberately narrow invariant: a later `if` is reportable only when an earlier
return under that same condition proves the later branch impossible and both
returns have the same source value. Reusing either diagnostic would widen the
rule to unrelated unreachable code and would not preserve the required
same-value predicate.

The rule therefore uses the already-selected, maintained `syn` parser rather
than adding a control-flow framework. Its small custom traversal records only
terminal-return proofs for equivalent source conditions and `match true`
arms. It invalidates proofs after a potential mutation, supports inline reason-bearing
suppression, and intentionally has no Rust baseline: the initial repository
scan must be clean.

## C13 package and test architecture (issue #7625)

`cargo_metadata` supplies the workspace package graph and distinguishes normal
from development dependencies, so package layering does not parse manifests.
`syn` supplies test attributes and path references for the source-local test
and renderer checks. The C13 leaf adds no dependency: no selected workspace
crate exposes a stable, Cargo-aware Rust module graph that resolves `#[path]`,
re-exports, and conditional modules. Adding one would violate the umbrella's
independent-leaf dependency contract. The rule consequently leaves package
edges to Cargo metadata and uses syntax only for source-local contracts; it
does not claim to implement a general module resolver.

## Duplicate-code detector (issue #7626)

Issue #7626 requires a Rust-native production duplicate-code gate. The survey
checked crates.io and repository metadata on 2026-07-17.

| Need | Candidates | Maintenance, license, and fit check | Selection |
|------|------------|-------------------------------------|-----------|
| Rust duplicate detection | [`dupes-core` / `cargo-dupes` 0.2.1](https://crates.io/crates/dupes-core), [`polydup` 0.9.3](https://crates.io/crates/polydup), [`find-dup-defs`](https://github.com/prostomarkeloff/find-dup-defs), [`jscpd` 5.x](https://www.npmjs.com/package/jscpd) | `dupes-core` is MIT and syn-based, but young (first release 2026-02-17, low download volume), function-unit oriented rather than arbitrary production blocks, walks the filesystem instead of the tracked-index contract, and would add workspace dependencies. `polydup` is MIT OR Apache-2.0 but pulls a Tree-sitter multi-language stack and is still early. `find-dup-defs` clusters top-level definitions only, so it misses block-level clones. `jscpd` is maintained and MIT, but ships as an external Node/binary workflow rather than an in-process `larch-lint` rule. | Do not adopt a third-party detector in this leaf. Implement a bespoke `duplicate-code` rule on the already-selected `syn` / `proc-macro2` stack so the gate stays inside the repository-policy runner, uses tracked-file discovery, and adds no root dependency. |

The bespoke rule normalizes production token streams (comments and formatting
dropped by lexing, `use` / `extern crate` skipped, generated markers and test
paths / `#[cfg(test)]` / `#[test]` skipped), reports exact cross-module clone
families at a fixed token threshold, and carries no baseline.
