### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/tests/support/shell_fixtures.py
- **Concern**: Plugin-tree builder omits checkout-delegation contract. Scenario: G-Fix-1: acceptance requires dispatching to real checkout scripts without copying them, but Approach only says symlink sources and test a benign entry; it never pins the delegate layout used by existing harnesses (generated python/cli.py, optional python/larch symlink, real CLI reached via repo_root() baked at build time). Piece 2+ migrations may ship incompatible trees.
- **Proposed resolution**: In Approach, specify a minimal delegate contract: build under tmp_path, symlink only requested checkout paths, generate python/cli.py that forwards argv to repo_root()/python/cli.py with repo_root() embedded at build time; test with one real verb (e.g. session validate-design-tmpdir or cli.py --help).

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: security
- **Location**: python/tests/support/shell_fixtures.py
- **Concern**: Plugin symlink targets lack repo containment. Scenario: G-Sec-4: builder resolves checkout sources via repo_root() but never requires targets stay inside that root or rejects symlink/.. escapes. A malicious or mistyped relative path could symlink outside the checkout.
- **Proposed resolution**: Before creating each symlink, resolve the source, require source.is_relative_to(repo_root()), reject non-regular files and symlink sources; raise a clear error on escape.

### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/tests/support/shell_fixtures.py
- **Concern**: Invocation-log JSON schema is unspecified. Scenario: G-Wire-1: acceptance calls for unambiguous invocation logs and Failure modes require strict JSON decoding, but no field set is named. Later harness ports may parse different shapes.
- **Proposed resolution**: Document and implement one NDJSON record shape (e.g. ordinal, argv list[str], returncode, stdout, stderr) in shell_fixtures.py and assert it in test_shell_fixtures.py.

### FINDING_4:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/tests/support/shell_fixtures.py
- **Concern**: Fake executable implementation medium is unspecified. Scenario: G-Py-4: argv must round-trip spaces, empty strings, Unicode, and embedded newlines without shell parsing; bash one-liners in existing tests are poor at JSON argv logging. A shell-based fake can reintroduce quoting regressions the kit is meant to replace.
- **Proposed resolution**: Require Python 3 fake executables (or a single shared Python dispatcher) that read sys.argv, append one JSON log line, emit configured stdout/stderr, and exit with configured status.

### FINDING_6:
- **Reviewer(s)**: Codex-Arch
- **Severity**: minor
- **Focus area**: security
- **Location**: python/tests/support/test_shell_fixtures.py (planned)
- **Concern**: Unsafe executable-name rejection lacks a planned self-test (G-Sec-1; G-Py-4). Scenario: A future implementation could accept slash, parent, or control characters and create an unsafe or ambiguous fake command while valid-name tests pass
- **Proposed resolution**: Add parametrized tests for unsupported, slash, parent, and NUL/control names; assert a clear exception and no filesystem entry is created 1. **Security, minor:** Add the rejection-path tests to verify the fail-closed boundary.

### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/tests/support/shell_fixtures.py
- **Concern**: PATH and handoff paths must be absolute resolved paths. Scenario: Controlled-env test runs subprocesses from an unrelated cwd. A relative fake-bin PATH entry or relative plugin/log path resolves against the child cwd, so stubs are skipped, live gh/codex/cursor/claude can run, and cwd-independence assertions fail or become flaky.
- **Proposed resolution**: Require resolved absolute Path/str for fake-bin PATH prefix, plugin root, and invocation-log paths in the factory contract; add an explicit plan bullet and a test that sets cwd away from tmp_path before exec and log reads.

### FINDING_8:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/tests/support/shell_fixtures.py
- **Concern**: Invocation-log JSON wire format is unspecified. Scenario: Acceptance requires unambiguous invocation logs, but the plan only says one JSON record per argv vector with no field names or file shape. Later partition migrations can diverge on NDJSON vs array files and key names.
- **Proposed resolution**: Pin a minimal stable schema in the plan (for example one NDJSON line per call with an argv list field, optional sequence index) and test strict decode of that shape.

### FINDING_9:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: code-quality
- **Location**: python/conftest.py
- **Concern**: Pyright cannot validate conftest fixture annotations. Scenario: python/pyrightconfig.json excludes conftest.py, yet the plan says precise conftest annotations let pyright validate consuming tests. Implementers may treat conftest typing as CI-gated when it is not.
- **Proposed resolution**: Anchor typed Protocols/classes in shell_fixtures.py (pyright-checked) and qualify the conftest bullet as thin pytest wrappers returning those types; keep pyright scoped to shell_fixtures.py and test modules unless exclude list changes. 1. **correctness** — `python/tests/support/shell_fixtures.py`: Controlled subprocess environments must publish absolute resolved paths for PATH entries, plugin roots, and log files. Relative fake-bin PATH entries break the planned unrelated-cwd test and can silently fall through to live vendor CLIs. 2. **architecture** — `python/tests/support/shell_fixtures.py`: Pin the invocation-log JSON contract (field names and NDJSON line shape). “One JSON record per argv” is not enough for contract-unification consumers in later partitions. 3. **code-quality** — `python/conftest.py`: Typed surfaces belong in `shell_fixtures.py`; conftest annotations are not pyright-gated today because `conftest.py` is excluded in `python/pyrightconfig.json`. **[OUT_OF_SCOPE]** — `python/tests/support/shell_fixtures.py`: Optional argv- or stdin-conditioned vendor stub scripting (codex `--output-last-message`, cursor JSON envelopes, claude stdin prompts) for migrations like `scripts/test-prompt-template-invariants.sh`. Piece 1 only needs static stdout/stderr/exit configuration; defer until a harness migration issue needs it. **[OUT_OF_SCOPE]** — `python/test_support.py`: Re-export shell fixture factories alongside `write_session_env` / `repo_root`. Conftest exposure satisfies piece-1 acceptance; `test_support` re-exports add API surface without a current consumer.

### FINDING_10:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/tests/support/shell_fixtures.py
- **Concern**: Plugin-tree builder omits the python/ layout thin wrappers require. Scenario: Acceptance requires dispatching real checkout scripts without copying them; wrappers such as skills/implement/scripts/step-5-review.sh exec python3 "$PLUGIN_ROOT/python/cli.py". A tree that only symlinks skill scripts cannot run those entries, so the planned plugin-dispatch self-test fails or future harness ports rediscover the Bash make_fake_step3_plugin pattern by hand
- **Proposed resolution**: Extend the plugin-tree builder to symlink repo_root()/python/larch, generate a minimal delegating python/cli.py that bakes repo_root() at creation time (not a runtime copy), and symlink requested checkout scripts/directories; keep the no-copy rule for real sources

### FINDING_11:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/tests/support/test_shell_fixtures.py
- **Concern**: CLAUDE_PLUGIN_ROOT isolation bullet lacks ambient leak setup. Scenario: The plan requires proving scrub still removes CLAUDE_PLUGIN_ROOT, but python/tests/test_conftest_session_isolation.py never exports CLAUDE_PLUGIN_ROOT in its module-scoped live-session fixture; a test that only asserts the var is absent during a normal run cannot catch regressions where a live /design or /implement session leaves plugin-root routing set
- **Proposed resolution**: Mirror test_conftest_session_isolation: add module-scoped ambient CLAUDE_PLUGIN_ROOT and LARCH_CLAUDE_PLUGIN_ROOT exports, then assert both are absent during the function-scoped scrub (either in test_shell_fixtures.py or by extending test_conftest_session_isolation.py and keeping the plan's regression command) 1. **correctness** — `python/tests/support/shell_fixtures.py` (plugin-tree section): The plugin-tree builder only symlinks requested checkout scripts and forbids copying runtime files, but standard larch checkout entries are thin Bash wrappers that immediately `exec python3 "$PLUGIN_ROOT/python/cli.py" …`. Without a fake `python/larch` symlink and a generated delegating `python/cli.py`, the acceptance criterion “dispatch to real checkout scripts without copying them” cannot be met for the scripts this kit is meant to replace. Existing Bash harnesses already use that layout (`skills/design/scripts/test-design-step3-review.sh` `make_fake_step3_plugin`). **Suggested revision:** add symlink `python/larch`, generate a minimal delegate `python/cli.py` with `repo_root()` baked in at build time, then symlink the requested script paths. 2. **correctness** — `python/tests/support/test_shell_fixtures.py` (session-isolation bullet): The plan calls for confirming `CLAUDE_PLUGIN_ROOT` scrub, but the referenced regression file does not currently seed ambient `CLAUDE_PLUGIN_ROOT` the way it does for `IMPLEMENT_TMPDIR` and related vars. A bare `assert "CLAUDE_PLUGIN_ROOT" not in os.environ` during a normal test would not catch a scrub regression under live-session conditions. **Suggested revision:** require module-scoped ambient exports for `CLAUDE_PLUGIN_ROOT` and `LARCH_CLAUDE_PLUGIN_ROOT`, matching the `#4495` pattern in `python/tests/test_conftest_session_isolation.py`.
