# scripts/test-implement-cleanup-roundtrip.sh — contract

Round-trip integration test for the `EXPECTED_TMPDIR_BASENAME_PREFIX` state-file convention used by `skills/implement/SKILL.md` Steps 13.5 and 14, and validated by Rust `implement_finalize_commands::cleanup_target_ok`.

## Purpose

Verifies that `read_state` (awk extraction) and `verify_cleanup_target` (case-glob) work end-to-end when the state file uses the unquoted prefix form (`EXPECTED_TMPDIR_BASENAME_PREFIX=claude-implement-${CLONE_TAG_FULL}-`). Also confirms via regression assertions (T4, T5) that the quoted form (`EXPECTED_TMPDIR_BASENAME_PREFIX="claude-implement-..."`) causes `read_state` to return a value with literal quote characters, making `verify_cleanup_target`'s case-glob fail to match any real basename — the bug fixed by #1572.

## Assertions

| ID | Description |
|----|-------------|
| T1 | Unquoted state file: `read_state` returns the prefix without a leading `"` character |
| T2 | Unquoted prefix matches a matching basename (verify_cleanup_target would authorize rm-rf) |
| T3 | Unquoted prefix does not match a different project's basename |
| T4 (regression) | Quoted state file: `read_state` returns the prefix **with** a leading `"` character (confirms the bug) |
| T5 (regression) | Quoted prefix does NOT match a matching basename (confirms verify_cleanup_target would refuse rm-rf) |

## Primary caller

None — standalone offline test. Referenced by `make lint` via the `test-implement-cleanup-roundtrip` target.

## Invariants

- The test creates its own sandbox under `/tmp` and cleans it up via `trap`.
- The awk extractor replicated here must stay in sync with the Rust state-wire parser.
- The case-glob replicated here must stay in sync with `cleanup_target_ok`.
- Edit in sync with: `crates/larch-cli/src/implement_finalize_commands.rs` (when state parsing or cleanup validation changes), `make test-implement-structure` assertion `(31e)` / `(31g)`, and `skills/implement/SKILL.md` Steps 13.5 / 14.

## Makefile wiring

Added to a `test-harnesses-N` shard and the `.PHONY` list as `test-implement-cleanup-roundtrip` (see `Makefile` / `make test-harness-shards-coverage`).
