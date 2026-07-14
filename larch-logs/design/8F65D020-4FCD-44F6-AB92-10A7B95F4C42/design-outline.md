## Proposed Design Outline

### Goals
- Add `python/tests/support/shell_fixtures.py` with typed fake-bin PATH factory, invocation logger, and minimal plugin-tree builder.
- Expose those fixtures as named pytest fixtures in `python/conftest.py`.
- Cover the new module with focused self-tests; make lint, type, and autouse-isolation checks pass.

### Non-goals
- Do not migrate or delete any existing Bash harness.
- Do not rebuild `repo_root()`, `RecordingRunner`, `write_session_env`, or session/tmpdir builders; consume them from the #7003 testkit already in place.
- Do not add shard-inventory entries or Makefile changes.

### Approach sketch
- `shell_fixtures.py` exports plain Python functions: `make_fake_bin_dir(tmp_path, name, ...)` writes an executable Python script that logs argv and returns configured output; `make_fake_plugin_tree(tmp_path)` builds a minimal `CLAUDE_PLUGIN_ROOT` tree that symlinks to the real repo scripts.
- `conftest.py` wraps the factory functions as scoped (not autouse) `@pytest.fixture` entries.
- Each fake binary appends an invocation record (argv list) to a per-directory log file.
- Self-tests cover argv-with-spaces, newline preservation, configured stdout/stderr/rc, PATH isolation, and plugin-tree dispatch.

### Surfaces in scope
- `python/tests/support/shell_fixtures.py` (new)
- `python/conftest.py` (extend with fixtures)
- `python/tests/support/test_shell_fixtures.py` (new, self-tests)

### Open questions
- None.
