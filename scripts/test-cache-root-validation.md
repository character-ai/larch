# scripts/test-cache-root-validation.sh — contract

Regression harness for the Python-owned larch session tmpdir validators widened
for cache-backed session roots:

- `python3 python/cli.py implement-finalize teardown` accepts state and tmpdir paths under that same root;
- `python3 python/cli.py token lane-write/lane-report` accepts the same root through `validate_dir`;
- legacy `/tmp/` and, when present, `/private/tmp/` remain accepted;
- unrelated paths remain rejected.

`session cleanup-tmpdir` moved to the Rust owner in issue #8057. Its cache-root
acceptance, `/tmp` acceptance, and unrelated-path rejection are pinned by the
`session-cleanup-tmpdir-*` cases in `crates/larch-cli/tests/parity.rs`.

Primary contract owners: `python/larch/state/finalize.py` and
`python/tokens.py research lane docs`.
