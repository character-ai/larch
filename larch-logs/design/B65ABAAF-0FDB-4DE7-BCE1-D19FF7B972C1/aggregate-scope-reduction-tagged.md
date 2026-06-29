### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation Phase2
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ruff.toml:308-310
- **Concern**: [SCOPE-REDUCTION] The shared `cli.py` ignore stays basename-wide, so the clean root `python/cli.py` shim remains exempt just because `python/larch/cli.py` still needs `C901`/`PLR0911`.. Scenario: After the split, `python/cli.py` still bypasses complexity enforcement and can grow new debt without `py-lint` catching it.
- **Proposed resolution**: Replace the basename row with a path-qualified `larch/cli.py` entry, or otherwise split the ignore so only the live package file keeps those codes.
