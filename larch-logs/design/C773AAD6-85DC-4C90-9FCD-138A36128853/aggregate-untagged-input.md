### FINDING_1:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/larch/lint/lint_module_manifest.py:main
- **Concern**: The required `run_rule` integration does not specify an on-disk inventory; its default discovery uses only `git ls-files --cached`.. Scenario: An untracked new `lint_*.py` module can lack a manifest entry without producing a finding, defeating the “every module” contract before staging.
- **Proposed resolution**: Require filesystem or cached-plus-untracked inventory enumeration, and test an untracked module through `main`; limit `run_rule` paths to the manifest and lint directory. 1. **[architecture] Filesystem inventory is not bound to the manifest lint.** The plan says to compare regular files, but also mandates `run_rule`, whose discovery path is cached Git files only. A contributor can add an untracked lint module and receive a clean result. Require explicit on-disk or cached-plus-untracked enumeration and a corresponding test.

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/lint/lint_module_manifest.py
- **Concern**: Manifest inventory must not use engine cached-only discovery. Scenario: The shared engine `run_rule` path calls `_discover_tracked_paths`, which runs `git ls-files --cached` only. Untracked `python/larch/lint/lint_*.py` files would be invisible, so a new module could ship without a manifest row and the commissioning backstop would not fire until after `git add`.
- **Proposed resolution**: Pin inventory to `lint_common.git_ls_files_z` with `--cached --others --exclude-standard` for `python/larch/lint/lint_*.py`, or to a guarded `Path.glob` with symlink rejection. State explicitly that manifest reconciliation must not reuse `_discover_tracked_paths`.

### FINDING_4:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/lint/lint_module_manifest.py:main/run_rule integration
- **Concern**: The planned run_rule integration still relies on the engine's cached-only Git inventory. Scenario: A new or symlinked lint_*.py present in the worktree but not yet indexed is omitted, so the manifest lint passes without enforcing its required inventory contract
- **Proposed resolution**: Require a root-aware worktree inventory preflight, or extend the engine to inspect tracked and untracked entries and reject unsafe ones; add an unindexed-file regression test 1. [correctness] `python/larch/lint/lint_module_manifest.py`: The plan still requires `run_rule`, whose inventory uses `git ls-files --cached`. Normal local runs can therefore miss new unindexed lint modules and cannot reject unindexed symlink entries, despite the feature requiring every on-disk `lint_*.py` to be checked. Add a root-aware inventory preflight or extend the engine, plus a regression test.
