# scripts/generators.tsv

`scripts/generators.tsv` is the registry consumed by `cargo run --quiet --locked --package larch-cli -- generate check`. Each non-comment row is a tab-separated `(generator-verb, output-path)` pair: column 1 is `generate <verb>`, matching a Rust CLI generator, and column 2 is the repo-relative committed artifact that the verb's `--check` mode validates.

The walker validates row shape, duplicate verbs, duplicate outputs, path hygiene, tracked output existence, and no post-run working-tree delta, then invokes each row in-process as `generate <verb> --check`.

Adding a row requires a registered `generate <verb>` entry in `crates/larch-cli/src/rendering_commands.rs`, focused Rust coverage, and a committed generated output path. Changes to registry grammar must update the Rust owner and its tests in the same PR. Generated artifact headers intentionally retain their historical Python command text so existing payload bytes remain stable.
