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
