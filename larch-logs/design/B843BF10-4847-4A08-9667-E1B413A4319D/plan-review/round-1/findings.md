### FINDING_1:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/cli.py:11-17
- **Concern**: Registry verb token forwarding is underspecified. Scenario: Plan says `target_main(rest_argv)` and failure mode #1 requires flags after `ship pr` to match today's `python/ship.py` argv, but `NEW: python/cli.py` never states that `rest_argv` excludes both domain and verb. An implementer can forward `["pr", "--branch", ...]` into `ship.main`, which will argparse-fail and break live `/implement` Step 8+.
- **Proposed resolution**: In `NEW: python/cli.py`, define `rest_argv` as argv tokens after `<domain> <verb>` only; add a dispatch unit test that `cli.py ship pr --branch foo` calls `ship.main` with `["--branch", "foo"]` (no `pr`).

### FINDING_2:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/migration_lint.py:21-22
- **Concern**: Manifest default path is documented as repo-root-relative while --root defaults to cwd with no join rule. Scenario: Running from a non-root cwd (or pytest fixtures that only set --root) resolves python/migrated-scripts.tsv against the wrong directory: empty/wrong manifest or spurious RETIRED_PATHS=0
- **Proposed resolution**: Specify that default --manifest is resolved as Path(--root) / python/migrated-scripts.tsv (or discover git toplevel once and join); add a test_migration_lint case with --root pointing at a fixture repo

### FINDING_3:
- **Reviewer(s)**: Codex-dyn-quiet-contract-drift
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:60,177; scripts/lib-quiet.md:18-19; scripts/lib-quiet.sh:166-172; python/logging_util.py:98-105
- **Concern**: [SCOPE-REDUCTION] Plan promotes emit_kv CR/LF rejection into a lint/CLI exit-2 mapping, but the existing shell spec only defines the shell helper returning 2 and the current Python API has no error mapper. Scenario: Implementer may add a broad ValueError-to-exit-2 wrapper around migration_lint even though its planned KV values are static counts/status; an internal bug would be reported as a usage/manifest error and the feature gains behavior not required by the fd-3 contract
- **Proposed resolution**: Add emit and emit_kv to logging_util with CR/LF ValueError coverage, but remove the lint maps ValueError to exit 2 edge case and any generic CLI caller mapping unless a concrete subcommand emits user-supplied KV values

### OOS_1:
- **Description**: Deleted harness drops LARCH_REPORT_TOKENS_REPO unsafe-slug subprocess coverage. Scenario: The plan retires skills/report-tokens/scripts/test-run-analysis-quiet.sh (exit-4 case at lines 104-118) but test_cli.py ported-wrapper cases only list bogus --skill and --plot-from; no python/ test currently covers LARCH_REPORT_TOKENS_REPO rejection
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: python/test_cli.py:41-43
- **Phase**: design

### OOS_2:
- **Description**: Deleted quiet harness design-path parity not named in plan test_cli.py. Scenario: The retired harness asserts design --skill output includes ### HARD under foreign quiet env (test-run-analysis-quiet.sh:61-74); the planned report-tokens quiet subprocess case only exercises implement
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: python/test_cli.py:41-42
- **Phase**: design
