### FINDING_1: Missing typed occurrence identity carrier
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: `Finding` cannot carry `pattern_name` and `occurrence`, so the occurrence baseline codec would have to parse rendered messages or line numbers, violating the required stable identity contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Extend Finding with optional pattern_name: str | None and occurrence: int | None (validated when the rule uses the occurrence codec), or add an explicit LintRule.project_occurrence_row(finding) hook; cover projection in test_lint_engine.py.
  - From Cursor-Innovation: Add a rule-selected occurrence projection path (codec hook) that bypasses `_project_finding` entirely for this rule; do not route these findings through generic or symbol-metric projection.
  - From Cursor-Innovation: Extend `Finding` with optional `pattern_name` and `occurrence` (or a dedicated occurrence-identity tuple) and teach the occurrence codec to read only those fields.
  - From Cursor-Pragmatic: In `### UPDATED: python/larch/lint/engine.py`, add optional `pattern_name` and `occurrence` on `Finding` (or a rule-specific projection input). Wire the occurrence codec to read those fields only. Extend engine tests to cover round-trip projection.
  - From Cursor-Requirements: Add optional pattern_name and occurrence fields on Finding (or an equivalent rule-local projection input named in engine.py) and wire the occurrence codec to read them directly.

### FINDING_2: Baseline path-prefix mismatch
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: The committed baseline uses `python/`-relative `file` values while engine findings and selectors use repo-relative paths, so naive projection will fail matching and rewrite every row.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Specify codec mapping: serialize file as Finding.path removeprefix python/; parse baseline file back to Finding.path with python/ prefix; add round-trip and no-op regen tests.
  - From Cursor-Pragmatic: Add to the occurrence codec plan: `OccurrenceBaselineRow.path` is repo-relative (`python/<file>`) for engine filtering while JSON keeps python/-relative `file`; or pin check-mode `paths=None` and document why. Add a regression test mirroring `test_paths_outside_scope_are_excluded_even_when_tracked`.
  - From Cursor-Requirements: Specify in the occurrence codec that baseline file is Finding.path with a leading python/ stripped, and add a round-trip test from repo-relative Finding.path to baseline file and back.

### FINDING_3: Existing main tests lack the git Runner contract
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Concern**: Existing `tmp_path` tests invoke `main()` without a git repository or injected Runner, but the engine-backed implementation requires git discovery before baseline behavior can be tested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Mirror lint_pylint_skip_file tests: reuse _git_ok_runner/_write_files from test_lint_engine.py, monkeypatch proc.ProcRunner in every main() test, and assert check/write/stale/malformed-python exit codes through the injected runner.

### FINDING_4: Thin adapter does not pin run_rule scope and stale behavior
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: major
- **Concern**: The adapter must explicitly preserve legacy check/write discovery and strict stale-row exit behavior; unspecified `run_rule` arguments can change scope and exit codes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Document in the REWRITTEN rule module: check uses paths=["python"] and strict_stale=True; write uses paths=None with rule discovery pathspecs python; keep --root/--write/--initial-reason mapping; add one main() test per exit path.
  - From Cursor-Innovation: In the thin adapter, call `run_rule` like `lint_pylint_skip_file`: `paths=["python"]` for check mode, `paths=None` only for `--write`, and `strict_stale=not write_baseline`; keep production filtering inside `detect`.

### FINDING_5: Production scope must filter before source loading
- **Reviewer(s)**: Codex-Arch, Cursor-Pragmatic, Codex-Pragmatic, Codex-Requirements
- **Severity**: major
- **Concern**: Engine discovery and source loading can process tracked files that legacy production-scope filtering would exclude, including tests, support files, non-Python paths, and symlinks; malformed or unreadable excluded files can therefore cause false failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add rule-owned pre-load discovery scope, including Python pathspecs and safe exclusion of legacy paths and symlinks, for both check and write modes. Define the compatibility treatment for the existing pylint engine client and cover scoped write discovery with an injected runner.
  - From Cursor-Pragmatic: Document check/write `paths=` and discovery behavior in the REWRITTEN rule module plan (for example: `paths=["python"]` only with repo-relative occurrence row `.path`, or `paths=None` with detector-side production scope filtering and a test that untracked `test_*.py` fixtures stay excluded). Reuse `_git_ok_runner` patterns from `test_lint_pylint_skip_file.py`.
  - From Codex-Pragmatic: Name an engine-level pre-load path filter or rule pathspec/filter contract that excludes the legacy paths and symlinks before `_load_source` and `_scan_source`, and cover it through the rule main with the injected runner.
  - From Codex-Requirements: Add rule-level pre-load source selection or pathspec filtering for `python/**/*.py` plus legacy exclusions, and test that malformed excluded files do not affect check or write modes.

### FINDING_6: No explicit occurrence baseline projection dispatch
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Concern**: Generic `_project_finding` rejects the rule’s `qualified_symbol`/missing-`metric` shape, and `run_rule` has no explicit occurrence-codec dispatch surface for parsing, projecting, comparing, and publishing occurrence rows.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add an explicit `LintRule` baseline-dispatch field and branch `_parse_baseline_row`, `_project_findings`, `_baseline_comparison`, `_rows_for_write`, and `_publish_baseline` through that hook for occurrence rows only.

### FINDING_7: Serializer does not preserve legacy baseline bytes
- **Reviewer(s)**: Cursor-Innovation, Cursor-Requirements
- **Severity**: major
- **Concern**: The generic serializer changes key names, key order, sorting, or formatting, so a no-op rewrite would not remain byte-identical to the committed legacy baseline.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Give the occurrence codec its own serializer: `file` key (python/-relative), legacy tuple sort, `indent=2`, no `sort_keys`, trailing newline; keep read-back validation against that format.
  - From Cursor-Requirements: Define the occurrence codec serializer to match legacy markdown output exactly: indent=2, no sort_keys, file/qualified_symbol/pattern_name/occurrence/reason field order, trailing newline; cover with the planned byte-identical rewrite test.

### FINDING_8: Missing-baseline clean-state behavior is unspecified
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Concern**: The engine may reject an absent baseline before scanning, changing the legacy behavior where a clean scan without a baseline succeeds while live findings without a baseline fail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add an occurrence-codec baseline flow that defers a missing-baseline error until after scanning: return 0 for no live findings and no baseline, retain exit 2 for live findings without one, and test both cases.

### FINDING_9:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/larch/lint/engine.py:964-976
- **Concern**: [SCOPE-REDUCTION] Write-mode discovery is wider than legacy python/-only scope. Scenario: G-Enf-2 / acceptance require byte-identical regen of python/markdown-heading-fence-state-baseline.json. Legacy _collect_all only walks root/python via iter_source_files. run_rule forbids paths on --write, so paths=None makes _discover_tracked_paths enumerate every tracked file (skills/*.py, scripts/*.py, etc.). Syntax policy raise and detect then run on out-of-scope .py files; regen can exit 2 or emit rows legacy never saw.
- **Proposed resolution**: Add rule-owned discovery pathspecs (default python) applied inside _scan_findings even when write_baseline=true and paths is None; pin the thin main adapter to that contract and add a test that tracked scripts/*.py or skills/*.py does not affect check/write.
