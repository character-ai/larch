# scripts/test-cache-root-validation.sh — contract

Regression harness for larch session tmpdir validators widened for
cache-backed session roots:

- `scripts/larch.sh implement-finalize teardown` accepts state and tmpdir paths under that same root;
- `scripts/larch.sh token lane-write` and `scripts/larch.sh token lane-report` (Rust-owned) accept the same root through `validate_dir`;
- legacy `/tmp/` and, when present, `/private/tmp/` remain accepted;
- unrelated paths remain rejected.

`session cleanup-tmpdir` moved to the Rust owner in issue #8057. Its cache-root
acceptance, `/tmp` acceptance, and unrelated-path rejection are pinned by the
`session-cleanup-tmpdir-*` cases in `crates/larch-cli/tests/parity.rs`.

Primary contract owner: `crates/larch-cli/src/implement_finalize_commands.rs`
and the Rust token commands reached through `scripts/larch.sh`.
