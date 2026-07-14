### [Plan Review] FINDING_1

### FINDING_1: Plugin-tree delegate layout
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic
- **Severity**: major
- **Concern**: The plugin-tree builder must provide the Python layout required by thin checkout wrappers while preserving the no-copy rule.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In Approach, specify a minimal delegate contract: build under tmp_path, symlink only requested checkout paths, generate python/cli.py that forwards argv to repo_root()/python/cli.py with repo_root() embedded at build time; test with one real verb (e.g. session validate-design-tmpdir or cli.py --help).
  - From Cursor-Pragmatic: Extend the plugin-tree builder to symlink repo_root()/python/larch, generate a minimal delegating python/cli.py that bakes repo_root() at creation time (not a runtime copy), and symlink requested checkout scripts/directories; keep the no-copy rule for real sources
  - From Cursor-Pragmatic: add symlink `python/larch`, generate a minimal delegate `python/cli.py` with `repo_root()` baked in at build time, then symlink the requested script paths.


### [Plan Review] FINDING_2

### FINDING_2: Symlink containment
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Concern**: Plugin-tree symlink targets are not constrained to the repository, allowing mistyped or malicious paths to escape the checkout.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Before creating each symlink, resolve the source, require source.is_relative_to(repo_root()), reject non-regular files and symlink sources; raise a clear error on escape.


### [Plan Review] FINDING_3

### FINDING_3: Absolute controlled-environment paths
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Concern**: Relative PATH, plugin-root, or log paths can resolve against an unrelated child cwd, causing fake tools to be skipped and live vendor CLIs to run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Require resolved absolute Path/str for fake-bin PATH prefix, plugin root, and invocation-log paths in the factory contract; add an explicit plan bullet and a test that sets cwd away from tmp_path before exec and log reads.


### [Plan Review] FINDING_4

### FINDING_4: Invocation-log schema
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: minor
- **Concern**: The invocation-log JSON wire format is unspecified, risking incompatible NDJSON shapes across later migrations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Document and implement one NDJSON record shape (e.g. ordinal, argv list[str], returncode, stdout, stderr) in shell_fixtures.py and assert it in test_shell_fixtures.py.
  - From Cursor-Innovation: Pin a minimal stable schema in the plan (for example one NDJSON line per call with an argv list field, optional sequence index) and test strict decode of that shape.


### [Plan Review] FINDING_5

### FINDING_5: Python fake executables
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Concern**: Shell-based fake executables could reintroduce quoting failures for spaces, empty strings, Unicode, and newlines.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Require Python 3 fake executables (or a single shared Python dispatcher) that read sys.argv, append one JSON log line, emit configured stdout/stderr, and exit with configured status.


### [Plan Review] FINDING_6

### FINDING_6: Unsafe executable-name tests
- **Reviewer(s)**: Codex-Arch
- **Severity**: minor
- **Concern**: The fail-closed boundary for unsafe fake executable names lacks planned self-tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add parametrized tests for unsupported, slash, parent, and NUL/control names; assert a clear exception and no filesystem entry is created 1. **Security, minor:** Add the rejection-path tests to verify the fail-closed boundary.


### [Plan Review] FINDING_7

### FINDING_7: Conftest typing boundary
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Concern**: `conftest.py` is excluded from Pyright, so its annotations cannot provide the stated type-checking guarantee.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Anchor typed Protocols/classes in shell_fixtures.py (pyright-checked) and qualify the conftest bullet as thin pytest wrappers returning those types; keep pyright scoped to shell_fixtures.py and test modules unless exclude list changes.


### [Plan Review] FINDING_9

### FINDING_9:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/tests/support/shell_fixtures.py
- **Concern**: [SCOPE-REDUCTION] Prefer baked repo_root over new runtime env wire. Scenario: G-Cfg-1 / G-Fix-1: harness lessons baked repo_root into fake cli.py instead of requiring per-invocation LARCH_TEST_REAL_REPO_ROOT. Adding a new env literal duplicates wire surface without config.py ownership.
- **Proposed resolution**: In the plugin-tree Approach, mandate embedding str(repo_root()) in generated delegate stubs; do not add LARCH_TEST_REAL_REPO_ROOT unless a later piece proves runtime override is required.


