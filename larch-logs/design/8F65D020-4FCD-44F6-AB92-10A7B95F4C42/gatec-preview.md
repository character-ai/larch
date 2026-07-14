## Final Design Plan

## Plan

Build a small, typed shell-test fixture layer on the landed #7023 and #7024 support modules. Keep every fixture opt-in and hermetic. Confidence: high.

### NEW: python/tests/support/shell_fixtures.py

- Define typed result and factory interfaces for fake executables, invocation logs, plugin trees, and subprocess environments.
- Support only `gh`, `codex`, `cursor`, and `claude` as fake external tools.
- Create executable fakes with configured stdout, stderr, and exit status.
- Record each argv vector as one JSON record. Preserve spaces, empty arguments, newlines, and argument boundaries without shell parsing.
- Install fail-closed defaults for every supported external tool. An unconfigured tool must return a clear failure instead of resolving to a live binary later in `PATH`.
- Build subprocess environment mappings without mutating `os.environ`. Put the fake-bin directory first, preserve required system command access, and allow explicit per-test overrides.
- Resolve checkout sources through `tests.support.repo_contract.repo_root()`, never cwd.
- Add a minimal plugin-tree builder that creates only requested layout and symlinks checkout scripts or directories. Do not copy runtime files.
- Reuse session and tmpdir helpers from `tests.support.session`. Do not add root lookup or environment-file writers.

#### Edge cases

- Reject unsupported or unsafe executable names.
- Handle repeated invocations and multiple configured tools without sharing logs between test directories.
- Preserve Unicode and embedded newlines in argv and configured output.
- Raise a clear error when a requested checkout source does not exist.
- Use `os.pathsep` and executable permission updates that work on supported macOS and Linux environments.

#### Failure modes

- Malformed or ambiguous logs could hide quoting regressions. Use structured JSON records and strict decoding.
- An incomplete fake tool set could invoke a developer's installed CLI. Provision fail-closed stubs for all four supported tools.
- Ambient cwd or environment state could change fixture behavior. Anchor paths to `repo_root()` and return fresh environment mappings.

### UPDATED: python/conftest.py

- Import the shell-fixture helpers under private aliases.
- Expose non-autouse, function-scoped fixtures for the fake-bin factory, controlled subprocess environment factory, and minimal plugin tree.
- Give fixture callables precise annotations so pyright can validate consuming tests.
- Keep the existing autouse session-routing scrub unchanged.
- Ensure fixture setup uses `tmp_path` and `monkeypatch` only where needed, so state and environment changes cannot escape a test.

### NEW: python/tests/support/test_shell_fixtures.py

- Test all four supported fake executable names.
- Verify exact argv round trips for spaces, empty strings, Unicode, and embedded newlines.
- Verify configured stdout, stderr, and non-zero exit status.
- Verify repeated calls produce distinct, ordered JSON invocation records.
- Prove unconfigured supported tools fail closed even when ambient `PATH` contains a same-named executable.
- Verify controlled environments do not mutate the parent process or leak between tests.
- Run fixtures from an unrelated cwd and confirm checkout resolution remains stable.
- Verify the plugin builder creates symlinks rather than copies and can dispatch a benign real checkout entry through the fake plugin root.
- Request the conftest fixtures directly to confirm their public names, types, function scope, and non-autouse behavior.
- Seed module-scoped ambient `CLAUDE_PLUGIN_ROOT` and `LARCH_CLAUDE_PLUGIN_ROOT` values, then assert the function-scoped autouse scrub removes both alongside existing session-routing variables.

## Testing strategy

- Run `python3 -m pytest python/tests/support/test_shell_fixtures.py -q`.
- Run `python3 -m pytest python/tests/support/test_foundation.py python/tests/test_conftest_session_isolation.py -q`.
- Run ruff and pylint against the three changed Python files.
- Run pyright against the changed fixture and test surfaces.
- Do not change Bash harnesses, shard assignments, or Makefile targets.

difficulty: MODERATE
diff_added: 468
diff_deleted: 0
mechanical_churn: false
diff_lines: 468
