### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/larch/lint/engine.py:964-976
- **Concern**: [SCOPE-REDUCTION] Write-mode discovery is wider than legacy python/-only scope. Scenario: G-Enf-2 / acceptance require byte-identical regen of python/markdown-heading-fence-state-baseline.json. Legacy _collect_all only walks root/python via iter_source_files. run_rule forbids paths on --write, so paths=None makes _discover_tracked_paths enumerate every tracked file (skills/*.py, scripts/*.py, etc.). Syntax policy raise and detect then run on out-of-scope .py files; regen can exit 2 or emit rows legacy never saw.
- **Proposed resolution**: Add rule-owned discovery pathspecs (default python) applied inside _scan_findings even when write_baseline=true and paths is None; pin the thin main adapter to that contract and add a test that tracked scripts/*.py or skills/*.py does not affect check/write.



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/larch/lint/engine.py:61-66
- **Concern**: Occurrence baseline identity has no typed Finding carrier. Scenario: Plan forbids deriving {pattern_name, occurrence} from rendered messages, but Finding only has path, line, rule_id, message, qualified_symbol, metric. _validate_finding rejects non-Finding returns and _project_finding cannot read occurrence keys. Wiring stock run_rule without new fields forces message parsing or breaks the five-key codec.
- **Proposed resolution**: Extend Finding with optional pattern_name: str | None and occurrence: int | None (validated when the rule uses the occurrence codec), or add an explicit LintRule.project_occurrence_row(finding) hook; cover projection in test_lint_engine.py.



### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/markdown-heading-fence-state-baseline.json
- **Concern**: Committed baseline file paths are python/-relative, not repo-relative. Scenario: Baseline rows use file values like larch/mod.py (see test _record and normalize_file_path). Engine findings and git discovery use repo-relative paths like python/larch/mod.py. An occurrence codec that maps Finding.path directly will rewrite file keys and fail byte-identical no-op regen (G-Enf-2).
- **Proposed resolution**: Specify codec mapping: serialize file as Finding.path removeprefix python/; parse baseline file back to Finding.path with python/ prefix; add round-trip and no-op regen tests.



### FINDING_4:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/tests/lint/test_lint_markdown_heading_fence_state.py:283-374
- **Concern**: tmp_path main() tests lack the git Runner contract run_rule requires. Scenario: After port, main will call run_rule with proc.ProcRunner(), which requires git rev-parse and git ls-files. Existing tests call lint.main(["--root", str(tmp_path)]) without a repo or monkeypatch; they pass today because main uses rglob only. Post-port they fail before baseline logic runs. G-Py-7.
- **Proposed resolution**: Mirror lint_pylint_skip_file tests: reuse _git_ok_runner/_write_files from test_lint_engine.py, monkeypatch proc.ProcRunner in every main() test, and assert check/write/stale/malformed-python exit codes through the injected runner.



### FINDING_5:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/lint/lint_markdown_heading_fence_state.py:847-869
- **Concern**: Thin main adapter does not pin pylint-parity run_rule wiring. Scenario: Legacy stale rows exit 2; engine defaults stale rows to warnings unless strict_stale=True. pylint main uses paths=[python/larch] on check, paths=None on write, and strict_stale=not write_baseline. Plan mentions strict stale and full-discovery write but not these kwargs. Omitted wiring can change exit codes and scope.
- **Proposed resolution**: Document in the REWRITTEN rule module: check uses paths=["python"] and strict_stale=True; write uses paths=None with rule discovery pathspecs python; keep --root/--write/--initial-reason mapping; add one main() test per exit path.



### FINDING_6:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/larch/lint/engine.py:926-1076; python/larch/lint/lint_pylint_skip_file.py:107-161
- **Concern**: Rule scope is not applied before source loading, contrary to G-Wire-3 and G-Py-4.. Scenario: In write mode `run_rule` rejects filtered paths, so the planned rule must discover every tracked file; detector-side filtering cannot prevent non-Python, excluded, or symlink paths from reaching `_load_source`, which raises on symlinks instead of preserving the legacy exclusion behavior.
- **Proposed resolution**: Add rule-owned pre-load discovery scope, including Python pathspecs and safe exclusion of legacy paths and symlinks, for both check and write modes. Define the compatibility treatment for the existing pylint engine client and cover scoped write discovery with an injected runner.



### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/lint/engine.py:757-772
- **Concern**: Stock `_project_finding` rejects findings that carry `qualified_symbol` without `metric`. Scenario: Markdown findings always set `qualified_symbol` and never set `metric`. Wiring this rule through unchanged `run_rule` projection raises `ScanError: baseline-active findings require qualified_symbol and metric together` on the first hit, so check/write never complete.
- **Proposed resolution**: Add a rule-selected occurrence projection path (codec hook) that bypasses `_project_finding` entirely for this rule; do not route these findings through generic or symbol-metric projection.



### FINDING_8:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/lint/engine.py:57-66
- **Concern**: `Finding` has no typed `pattern_name`/`occurrence` fields. Scenario: The plan forbids deriving occurrence identity from rendered messages or line numbers, but the engine dataclass only has `qualified_symbol` and `metric`. Without new fields (or an equally explicit carrier), the codec must parse `message` or overload `metric`, breaking stable `{file, qualified_symbol, pattern_name, occurrence}` identity and the equivalence goldens.
- **Proposed resolution**: Extend `Finding` with optional `pattern_name` and `occurrence` (or a dedicated occurrence-identity tuple) and teach the occurrence codec to read only those fields.



### FINDING_9:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/lint/engine.py:847-870
- **Concern**: Occurrence baseline serialization is not pinned to the legacy byte shape. Scenario: Acceptance requires a byte-identical no-op rewrite of `python/markdown-heading-fence-state-baseline.json`. Stock `_serialized_baseline` uses `sort_keys=True` and `path` keys; legacy rows use `file` first with fixed key order and `json.dumps(..., indent=2)` without `sort_keys`. Reusing the generic writer reorders keys and breaks the committed baseline on regeneration.
- **Proposed resolution**: Give the occurrence codec its own serializer: `file` key (python/-relative), legacy tuple sort, `indent=2`, no `sort_keys`, trailing newline; keep read-back validation against that format.



### FINDING_10:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/lint/lint_markdown_heading_fence_state.py:847-869
- **Concern**: `main` does not pin `run_rule` stale and discovery knobs. Scenario: Legacy check always fail-closes on stale rows (exit 2). Stock `run_rule` warns on stale unless `strict_stale=True`. Legacy discovery never leaves `python/` production scope; `paths=None` makes the engine load every tracked repo file. Stale-only and unreadable non-`python/` tracked files can change exit behavior versus today.
- **Proposed resolution**: In the thin adapter, call `run_rule` like `lint_pylint_skip_file`: `paths=["python"]` for check mode, `paths=None` only for `--write`, and `strict_stale=not write_baseline`; keep production filtering inside `detect`.



### FINDING_11:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/larch/lint/engine.py:1033-1102
- **Concern**: `run_rule` has no explicit occurrence-codec dispatch surface. Scenario: The plan puts an occurrence codec on `LintRule` and routes baseline I/O through `run_rule`, but the driver hardcodes generic/symbol-metric parse, project, compare, and publish helpers. Without a named hook (for example `baseline_codec` / `baseline_kind` on `LintRule`), implementers must fork `run_rule` internals and risk drift from the pylint port pattern.
- **Proposed resolution**: Add an explicit `LintRule` baseline-dispatch field and branch `_parse_baseline_row`, `_project_findings`, `_baseline_comparison`, `_rows_for_write`, and `_publish_baseline` through that hook for occurrence rows only.



### FINDING_12:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/lint/engine.py:1062-1072; python/larch/lint/lint_markdown_heading_fence_state.py:859-869
- **Concern**: run_rule baseline mapping lacks the rule’s absent-baseline clean-state contract. Scenario: The committed markdown baseline is currently absent. Legacy check returns 0 when the scan has no findings and no baseline, but run_rule rejects the missing path before scanning, so make lint-markdown-heading-fence-state exits 2 on a clean tree.
- **Proposed resolution**: Add an occurrence-codec baseline flow that defers a missing-baseline error until after scanning: return 0 for no live findings and no baseline, retain exit 2 for live findings without one, and test both cases.



### FINDING_13:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/lint/engine.py:790-810
- **Concern**: Occurrence baseline rows use python/-relative `file` keys but `_selected_baseline_rows` matches `row.path` against repo-relative selectors. Scenario: Committed rows look like `{"file":"larch/mod.py",...}`. If the thin adapter copies `lint_pylint_skip_file.main` and passes `paths=["python"]` on check, every occurrence row fails `_row_matches_selector` because `larch/mod.py` does not start with `python/`. Scoped baseline becomes empty, live findings look unbaselined, and `make lint-markdown-heading-fence-state` exits 1 on the current tree.
- **Proposed resolution**: Add to the occurrence codec plan: `OccurrenceBaselineRow.path` is repo-relative (`python/<file>`) for engine filtering while JSON keeps python/-relative `file`; or pin check-mode `paths=None` and document why. Add a regression test mirroring `test_paths_outside_scope_are_excluded_even_when_tracked`.



### FINDING_14:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/lint/engine.py:57-66
- **Concern**: Plan requires typed `pattern_name`/`occurrence` baseline identity without parsing messages, but `Finding` has no fields to carry them. Scenario: The adapter must emit occurrence identity from detector output. Stock `Finding` only has `path`, `line`, `rule_id`, `message`, `qualified_symbol`, and `metric`. `_project_findings` cannot build `{file, qualified_symbol, pattern_name, occurrence, reason}` rows without re-parsing the rendered message, which the plan forbids.
- **Proposed resolution**: In `### UPDATED: python/larch/lint/engine.py`, add optional `pattern_name` and `occurrence` on `Finding` (or a rule-specific projection input). Wire the occurrence codec to read those fields only. Extend engine tests to cover round-trip projection.



### FINDING_15:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/larch/lint/lint_markdown_heading_fence_state.py:147-170
- **Concern**: CLI `paths=` / discovery contract for check vs write is unspecified beyond "map to run_rule". Scenario: Legacy discovery walks only `python/` production files via `iter_source_files`. `run_rule` check mode typically passes scoped `paths`, while write mode requires `paths=None` and full `git ls-files`. Without an explicit contract, implementers can combine scoped `paths=["python"]` with python/-relative occurrence rows and break baseline checks, or use `paths=None` and run `ScanError` syntax probes on every tracked repo file before `detect()` can exclude it.
- **Proposed resolution**: Document check/write `paths=` and discovery behavior in the REWRITTEN rule module plan (for example: `paths=["python"]` only with repo-relative occurrence row `.path`, or `paths=None` with detector-side production scope filtering and a test that untracked `test_*.py` fixtures stay excluded). Reuse `_git_ok_runner` patterns from `test_lint_pylint_skip_file.py`.



### FINDING_16:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: python/larch/lint/engine.py:195-325
- **Concern**: Production-scope exclusions must occur before engine source loading and syntax handling. Scenario: The engine loads and parses every git-listed path before detect runs. A tracked excluded test, support, directory file, or symlink can therefore trigger an unreadable or malformed-Python exit 2 instead of being skipped as the legacy production scan did.
- **Proposed resolution**: Name an engine-level pre-load path filter or rule pathspec/filter contract that excludes the legacy paths and symlinks before `_load_source` and `_scan_source`, and cover it through the rule main with the injected runner.



### FINDING_17:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/larch/lint/engine.py:58-67
- **Concern**: The occurrence codec has no typed carrier on Finding. Scenario: The REWRITTEN rule says detect emits engine Finding values with pattern_name and occurrence baseline identity, and the codec must project detector-supplied fields without parsing rendered messages. Stock Finding only has path, line, rule_id, message, qualified_symbol, and metric, so run_rule cannot build {file, qualified_symbol, pattern_name, occurrence, reason} rows without re-deriving identity from message text.
- **Proposed resolution**: Add optional pattern_name and occurrence fields on Finding (or an equivalent rule-local projection input named in engine.py) and wire the occurrence codec to read them directly.



### FINDING_18:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/lint/engine.py:648-870
- **Concern**: Baseline file paths use a different prefix than Finding.path. Scenario: Committed rows and tests use python/-relative file values such as larch/mod.py, while git discovery and engine findings use repo-relative paths such as python/larch/mod.py. The equivalence adapter already prepends python/ when mapping legacy findings. A naive codec that writes Finding.path into file will not load or match the committed baseline, and no-op regeneration will rewrite every row.
- **Proposed resolution**: Specify in the occurrence codec that baseline file is Finding.path with a leading python/ stripped, and add a round-trip test from repo-relative Finding.path to baseline file and back.



### FINDING_19:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/lint/engine.py:847-870
- **Concern**: Occurrence baseline serialization must match legacy bytes. Scenario: Acceptance requires a byte-identical no-op rewrite of python/markdown-heading-fence-state-baseline.json. Legacy serialize_baseline uses json.dumps(ordered, indent=2) plus a trailing newline with record field order and no sort_keys. Stock engine _serialized_baseline uses sort_keys=True and different key names, which changes bytes even when identities match.
- **Proposed resolution**: Define the occurrence codec serializer to match legacy markdown output exactly: indent=2, no sort_keys, file/qualified_symbol/pattern_name/occurrence/reason field order, trailing newline; cover with the planned byte-identical rewrite test.



### FINDING_20:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/lint/engine.py:926-955
- **Concern**: Production scope filtering is not specified before source loading and syntax handling. Scenario: `run_rule` currently loads every tracked file and applies Python syntax policy before `detect`; a malformed excluded test or support `.py` file now exits 2 although legacy discovery skipped it.
- **Proposed resolution**: Add rule-level pre-load source selection or pathspec filtering for `python/**/*.py` plus legacy exclusions, and test that malformed excluded files do not affect check or write modes.



