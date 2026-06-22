### [Plan Review] FINDING_4

### FINDING_4:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/ruff-complexity-audit.toml
- **Concern**: [SCOPE-REDUCTION] Audit config is over-specified to mirror main `python/ruff.toml` global ignores. Scenario: The audit pass is invoked with `--select C901,PLR0911,PLR0912,PLR0913,PLR0915`, so the long `[lint] ignore` list from main config is inert noise; duplicating it adds ~70 lines of drift-prone config unrelated to the issue’s “one config + docs” intent
- **Proposed resolution**: Make `ruff-complexity-audit.toml` minimal: copy `target-version` and `exclude` from `python/ruff.toml`, set `[lint] select` to the five complexity codes only, and keep just the test/harness `[lint.per-file-ignores]` entries; do not copy the main global ignore list


### [Plan Review] FINDING_5

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/ruff-complexity-audit.toml:1-87
- **Concern**: [SCOPE-REDUCTION] Duplicate full `[lint] ignore` blocks in two TOML files will drift. Scenario: Plan copies the entire global ignore list into `ruff-complexity-audit.toml` while `python/ruff.toml` keeps its own copy; a later ignore-only edit to one file changes audit vs main rule selection and can false-pass or false-fail the baseline ratchet
- **Proposed resolution**: Make `python/ruff-complexity-audit.toml` the shared base (complexity codes enabled, test/harness per-file ignores only) and add `extend = "ruff-complexity-audit.toml"` to `python/ruff.toml` for production grandfather entries; audit subprocess keeps using the base config only


