### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:190-195
- **Concern**: migrated-scripts.tsv subsection lists only two of four required retirement rows despite prose requiring helper and harness siblings. Scenario: Implementer adds only oos-file-conflict-deps.sh/.md rows; test-oos-file-conflict-deps.sh/.md stay unregistered so make lint-retired-scripts no longer guards harness literals in agent-lint.toml and docs/linting.md after deletion
- **Proposed resolution**: Under ### UPDATED: python/migrated-scripts.tsv enumerate all four paths: skills/implement/scripts/oos-file-conflict-deps.sh, skills/implement/scripts/oos-file-conflict-deps.md, skills/implement/scripts/test-oos-file-conflict-deps.sh, skills/implement/scripts/test-oos-file-conflict-deps.md

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/oos_filer.py:788-794
- **Concern**: Plan requires operator-visible **⚠ /implement: oos-file-conflict pre-pass failed** on non-zero CLI exit but only names _append_tool_failure. Scenario: _append_tool_failure writes execution-issues.md only; python/cli.py oos file stdout is JSON-only on the Python ship path so operators may see silent degrade with no breadcrumb
- **Proposed resolution**: In ### UPDATED: python/oos_filer.py branch 3 specify stderr print (or a JSON payload field the ship driver surfaces) for the exact warning string in addition to _append_tool_failure

### FINDING_3:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/migrated-scripts.tsv:190-195
- **Concern**: `### UPDATED: python/migrated-scripts.tsv` names only helper `.sh`/`.md` while Approach, failure modes, and acceptance require all four retired paths. Scenario: Deleting the harness without manifest rows for `skills/implement/scripts/test-oos-file-conflict-deps.sh` and `.md` leaves stale references in `Makefile`, `agent-lint.toml`, `docs/linting.md`, and `scripts/residual-bash-paths.txt` unenforced; `make lint-retired-scripts` can pass while broken harness literals remain
- **Proposed resolution**: Add explicit bullets for `skills/implement/scripts/test-oos-file-conflict-deps.sh` and `skills/implement/scripts/test-oos-file-conflict-deps.md` in the migrated-scripts.tsv section (same `#4967` rows as the helper siblings)

### FINDING_4:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: architecture
- **Location**: <TMPDIR>/plan.txt:190-195
- **Concern**: Manifest subsection says all four retired paths but lists only the helper .sh/.md rows. Scenario: The harness .sh/.md files are also deleted, but missing manifest rows would leave retired harness references unenforced after the migration
- **Proposed resolution**: Add the two missing rows: skills/implement/scripts/test-oos-file-conflict-deps.sh and skills/implement/scripts/test-oos-file-conflict-deps.md
