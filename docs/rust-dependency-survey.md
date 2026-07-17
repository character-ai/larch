# Rust Dependency Survey

Issue #7602 establishes the Rust workspace before larch runtime migration.
The survey checked current crates.io metadata, repository activity, and license
metadata on 2026-07-17. All candidates below were active and unarchived.

| Need | Candidates | Maintenance and license check | Selection |
|------|------------|-------------------------------|-----------|
| CLI parsing | [`clap` 4.6.2](https://crates.io/crates/clap/4.6.2), [`bpaf` 0.9.26](https://crates.io/crates/bpaf/0.9.26) | Repositories active 2026-07-17 and 2026-07-15. Both are unarchived and MIT OR Apache-2.0. | Use `clap`. It supplies derive-based parsing and stable help/version output. `bpaf`'s combinator model adds no benefit for the planned subcommand CLI. |
| Serialization | [`serde` 1.0.228](https://crates.io/crates/serde/1.0.228), [`simd-json` 0.17.3](https://crates.io/crates/simd-json/0.17.3) | Repositories active 2026-07-11 and 2026-07-14. Both are unarchived and MIT OR Apache-2.0. | Reserve `serde` for typed wire data, but do not add it until a wire format exists. `simd-json`'s mutable-buffer and performance focus do not fit small lint metadata. |
| CLI assertions | [`assert_cmd` 2.2.2](https://crates.io/crates/assert_cmd/2.2.2) with [`predicates` 3.1.4](https://crates.io/crates/predicates/3.1.4), [`trycmd` 1.2.0](https://crates.io/crates/trycmd/1.2.0) | Repositories active 2026-07-16, 2026-07-09, and 2026-07-09. All are unarchived and MIT OR Apache-2.0. | Reserve `assert_cmd` and `predicates` for the F2 CLI harness. F1 uses Clap's built-in validator. `trycmd` snapshots would make small diagnostic changes costly. |
| Cargo integration | [`cargo_metadata` 0.23.1](https://crates.io/crates/cargo_metadata/0.23.1), [`guppy` 0.17.26](https://crates.io/crates/guppy/0.17.26) | Repositories active 2026-04-10 and 2026-06-04. Both are unarchived. `cargo_metadata` is MIT; `guppy` is MIT OR Apache-2.0. | Reserve `cargo_metadata` for direct Cargo graph access, but do not add it before a rule needs Cargo data. `guppy`'s graph analysis is broader than the planned workspace queries. |
| Dependency policy | [`cargo-deny` 0.20.2](https://crates.io/crates/cargo-deny/0.20.2) | Repository active 2026-07-09, unarchived, and MIT OR Apache-2.0. | Use `cargo-deny`. One gate covers advisories, licenses, duplicate versions, wildcard requirements, and untrusted sources. |

The selected runtime dependency is `clap`. Deferred selections stay out of
`Cargo.lock` until code uses them. This keeps the foundation minimal and makes
future dependency additions explicit review points.
