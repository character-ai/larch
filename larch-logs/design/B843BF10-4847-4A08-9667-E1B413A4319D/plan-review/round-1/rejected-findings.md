### [Plan Review] FINDING_1

### FINDING_1: CLI dispatcher may forward verb token into target main
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Concern**: The dispatcher contract does not clearly state that `rest_argv` excludes both `<domain>` and `<verb>`, creating a risk that `cli.py ship pr --branch foo` forwards `["pr", "--branch", "foo"]` to `ship.main` instead of only the remaining flags.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: In `NEW: python/cli.py`, define `rest_argv` as argv tokens after `<domain> <verb>` only; add a dispatch unit test that `cli.py ship pr --branch foo` calls `ship.main` with `["--branch", "foo"]` (no `pr`).


### [Plan Review] FINDING_2

### FINDING_2: Manifest default may resolve relative to the wrong directory
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The default retired-scripts manifest path is described as repo-root-relative, but `--root` defaults to the current working directory without a specified join/discovery rule, so non-root invocations may scan with the wrong or missing manifest.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Specify that default --manifest is resolved as Path(--root) / python/migrated-scripts.tsv (or discover git toplevel once and join); add a test_migration_lint case with --root pointing at a fixture repo


### [Plan Review] FINDING_3

### FINDING_3:
- **Reviewer(s)**: Codex-dyn-quiet-contract-drift
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:60,177; scripts/lib-quiet.md:18-19; scripts/lib-quiet.sh:166-172; python/logging_util.py:98-105
- **Concern**: [SCOPE-REDUCTION] Plan promotes emit_kv CR/LF rejection into a lint/CLI exit-2 mapping, but the existing shell spec only defines the shell helper returning 2 and the current Python API has no error mapper. Scenario: Implementer may add a broad ValueError-to-exit-2 wrapper around migration_lint even though its planned KV values are static counts/status; an internal bug would be reported as a usage/manifest error and the feature gains behavior not required by the fd-3 contract
- **Proposed resolution**: Add emit and emit_kv to logging_util with CR/LF ValueError coverage, but remove the lint maps ValueError to exit 2 edge case and any generic CLI caller mapping unless a concrete subcommand emits user-supplied KV values


