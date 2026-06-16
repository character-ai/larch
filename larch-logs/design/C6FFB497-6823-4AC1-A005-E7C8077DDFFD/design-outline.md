## Proposed Design Outline

### Goals
- Retire `scripts/lib-design-tmpdir.sh`: delete the bash lib, its `.md`, and its test harness.
- Give bash callers a CLI surface for the already-ported `session_env.validate_design_tmpdir`.
- Repoint all 14 live bash sourcers with identical fail-fast (`exit 2`) behavior.

### Non-goals
- Porting `skills/implement/scripts/lib-resolve-implement-tmpdir.sh` (bash-hook-sourced); split to a new follow-up tracking issue.
- Touching the 2 already-migrated libs (`lib-validate-meta-path.sh` #4333, `lib-finalize-state-keys.sh` #3690).
- Reimplementing validation logic or refactoring the 14 wrappers beyond the source-to-CLI swap.

### Approach sketch
- Add `validate_design_tmpdir_main(argv)` to `python/session_env.py`; route `("session", "validate-design-tmpdir")` in `python/cli.py`. Exit 0 on ok, 2 on failure, message to stderr.
- Replace `source .../lib-design-tmpdir.sh` + `larch_design_tmpdir_validate "$X" || exit 2` with `python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" session validate-design-tmpdir "$X" || exit 2` in each sourcer, preserving pause-before-work ordering.
- Delete the bash lib + `.md` + harness; append the 4 paths to `python/migrated-scripts.tsv` (#3780); drop the `python/checks.py` allowlist row, the `Makefile` `test-lib-design-tmpdir` target, and any `agent-lint.toml` allowlist entry.
- Add `python/test_session_env.py` coverage for the new verb.

### Surfaces in scope
- `python/session_env.py`, `python/cli.py`, `python/test_session_env.py`
- `scripts/lib-design-tmpdir.{sh,md}`, `scripts/test-lib-design-tmpdir.{sh,md}` (delete)
- 14 wrapper `.sh` files under `scripts/` and `skills/design/scripts/`
- `python/migrated-scripts.tsv`, `python/checks.py`, `Makefile`, `agent-lint.toml`

### Open questions
- None. Scope resolved in Round 1.
