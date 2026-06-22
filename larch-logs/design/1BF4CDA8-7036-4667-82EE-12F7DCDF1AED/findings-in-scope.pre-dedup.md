### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:96-108
- **Concern**: Baseline JSON wire-shape example is invalid JSON. Scenario: The second sample record omits its opening `{`, so copy-paste generation of `python/complexity-baseline.json` can produce a manifest that fails `load_baseline` exit 2 on first CI run
- **Proposed resolution**: Fix the illustrative array to include a `{` before the `ship.py` record (or drop the broken multi-record sample and keep the single-record example only)



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/lint_complexity_baseline.py
- **Concern**: Plan omits ruff non-zero exit handling for the audit subprocess. Scenario: Audit-config `ruff check` over grandfathered production code will exit 1 while still emitting violation JSON; treating any non-zero ruff exit as a hard failure would abort before baseline comparison and break `make py-lint-main` on the unchanged tree
- **Proposed resolution**: Document and implement: always parse `--output-format json` stdout for the five selected rules; treat ruff exit 0 and 1 as success paths when JSON parses; reserve exit 2 for missing ruff, empty/unparseable JSON, or unexpected ruff exit codes



### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/ruff-complexity-audit.toml
- **Concern**: [SCOPE-REDUCTION] Audit config is over-specified to mirror main `python/ruff.toml` global ignores. Scenario: The audit pass is invoked with `--select C901,PLR0911,PLR0912,PLR0913,PLR0915`, so the long `[lint] ignore` list from main config is inert noise; duplicating it adds ~70 lines of drift-prone config unrelated to the issue’s “one config + docs” intent
- **Proposed resolution**: Make `ruff-complexity-audit.toml` minimal: copy `target-version` and `exclude` from `python/ruff.toml`, set `[lint] select` to the five complexity codes only, and keep just the test/harness `[lint.per-file-ignores]` entries; do not copy the main global ignore list



### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/ruff-complexity-audit.toml:1-87
- **Concern**: [SCOPE-REDUCTION] Duplicate full `[lint] ignore` blocks in two TOML files will drift. Scenario: Plan copies the entire global ignore list into `ruff-complexity-audit.toml` while `python/ruff.toml` keeps its own copy; a later ignore-only edit to one file changes audit vs main rule selection and can false-pass or false-fail the baseline ratchet
- **Proposed resolution**: Make `python/ruff-complexity-audit.toml` the shared base (complexity codes enabled, test/harness per-file ignores only) and add `extend = "ruff-complexity-audit.toml"` to `python/ruff.toml` for production grandfather entries; audit subprocess keeps using the base config only



### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/complexity-baseline.json:96-108
- **Concern**: Plan wire-shape JSON example is syntactically invalid. Scenario: The sample array closes the first object then lists bare `"file": "ship.py"` keys without a second `{`; an implementer copying the plan example produces malformed JSON and fails `load_baseline` exit 2
- **Proposed resolution**: Fix the plan example to a valid two-element array with both objects fully braced; keep the normative top-level-array contract unchanged



### FINDING_6:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/lint_complexity_baseline.py:132-140
- **Concern**: Treat ruff exit code 1 as a normal violations-present outcome when parsing audit JSON. Scenario: On the audit-config scan, production modules intentionally still emit complexity diagnostics, so `ruff check` exits 1 while printing the JSON payload. If `main()` uses `check=True`, maps any non-zero ruff rc to exit 2, or otherwise aborts before parsing stdout on rc 1, `python/cli.py lint complexity-baseline` fails on every run and `make py-lint-main` stays red after merge.
- **Proposed resolution**: Run ruff with `check=False`; accept rc 0 (no records) and rc 1 (parse stdout JSON); reserve exit 2 for rc >= 2, empty/unparseable JSON, or spawn failures. Document the same semantics for the manual baseline-derivation command (rc 1 is expected when violations exist).



### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/lint_complexity_baseline.py:126-127
- **Concern**: Normalize ruff `filename` values before baseline indexing. Scenario: Audit runs with `cwd=python/`, so ruff JSON may use `ship.py` or `./ship.py`. If generation writes `ship.py` in `complexity-baseline.json` but a later parse keeps `./ship.py` (or mixes `python/` prefixes), comparison reports spurious new identities and CI false-fails until manual rebaseline.
- **Proposed resolution**: Centralize filepath normalization in `parse_violation_record` (strip leading `./` and optional `python/`; use forward-slash repo-relative paths under `python/`) and reuse it for per-file-ignore grouping during baseline generation.



