### FINDING_1: Declaration-line suppression is incompatible with engine suppression
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Requirements, Codex-Requirements, Cursor-dyn-Lint Parity Auditor, Codex-dyn-Lint Parity Auditor
- **Severity**: major
- **Concern**: Existing pragmas suppress regex declarations, while engine suppression checks emitted finding lines. Porting directly would break valid declaration pragmas and empty-reason failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Set LintRule.allow_inline_suppression=False. Keep declaration-line pragma parsing inside detect (or a detect helper). Update the plan and tests to say this rule uses detector-owned suppression, not engine same-line suppression.
  - From Codex-Arch: Disable engine inline suppression for this rule; keep pragma parsing inside `detect`; adjust planned tests accordingly.
  - From Cursor-Innovation: Set `allow_inline_suppression=False`, keep declaration-line pragma handling inside `detect`, and change the test plan to verify detect-local suppression rather than engine post-filter suppression.
  - From Codex-Innovation: Add a compatibility suppression hook that preserves declaration-line semantics and test both accepted and empty declaration pragmas through `main`.
  - From Cursor-Requirements: Pin `allow_inline_suppression=false` and keep declaration-line PRAGMA handling inside detect() using SourceFile text/token comments; drop engine-suppression wording from tests unless finding-line suppressions are intentionally added
  - From Codex-Requirements: Revise the detector or engine suppression contract to preserve declaration-line pragma handling, including empty-reason failure, and add regression coverage for the documented declaration form
  - From Cursor-dyn-Lint Parity Auditor: docs/linting.md requires suppression on the regex declaration. Engine `_apply_inline_suppressions` only checks finding.line. Legacy `_record_heading_regex` suppresses at declaration lineno before the regex enters scope. Wording "verify engine suppression" risks testing only the engine pragma path. State detect owns declaration-line pragma parsing (including empty-reason ScanError). Engine suppression covers match-line findings only. Add an explicit detect-level test contract in the plan.
  - From Codex-dyn-Lint Parity Auditor: Add engine support for a detector-supplied suppression anchor while retaining the rendered match line, and cover the declaration-line pragma through `main`.


### FINDING_2: Syntax-error exit behavior is unspecified
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-Lint Parity Auditor, Codex-dyn-Lint Parity Auditor
- **Severity**: major
- **Concern**: The current rule raises `ScanError` and exits 2 on malformed Python, while engine `fail` or `skip` policies produce exit 1 or 0.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Spell out the carve-out: preserve ScanError-based exit 2 for unreadable or unparseable sources, and add an explicit test that engine syntax_policy does not replace that path. If detect must run via SourceFile, document how detect raises ScanError without relying on engine syntax findings.
  - From Codex-Arch: Specify that `detect` or `main` must raise `ScanError` on `SyntaxError`, preserving exit 2, unless tests and docs intentionally change.
  - From Cursor-Innovation: State explicitly that `detect` (or `main` before `run_rule`) must raise `ScanError` on `SyntaxError` to preserve exit 2, or update the planned `main` tests if semantics intentionally change.
  - From Cursor-Pragmatic: Either keep parse failures as ScanError on the markdown path (detect/main wrapper before engine emission), or document and update the exit-2 test to the new engine contract. Do not silently drift while claiming preserved exit codes.
  - From Cursor-Requirements: Pin syntax_policy and exit behavior in the REWRITTEN section: either document the intentional shift to an engine syntax finding (and update the named test/acceptance), or add a thin main() shim that maps engine syntax findings to exit 2 before CI runs
  - From Cursor-dyn-Lint Parity Auditor: Specify LintRule.syntax_policy=skip and have detect raise ScanError on parse failure, or document and test the intentional exit-1 change. Plan must pick one to preserve acceptance.
  - From Codex-dyn-Lint Parity Auditor: Add an engine syntax-error mode that reports a scan error and exits 2, then retain the malformed-source CLI test.


### FINDING_4: Legacy baseline schema and identity are incompatible with stock `run_rule`
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements, Cursor-dyn-Lint Parity Auditor, Codex-dyn-Lint Parity Auditor
- **Severity**: major
- **Concern**: The committed baseline uses `{file, qualified_symbol, pattern_name, occurrence, reason}` and line-independent occurrence identity. Generic and symbol-metric engine rows cannot load, compare, or byte-stably rewrite it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add a firm `engine.py` and engine-test update for a typed legacy-baseline codec/projection that preserves this rule’s exact schema and identity, then have the thin rule use that codec.
  - From Codex-Arch: Use the engine for git-tracked discovery, `SourceFile` loading, dedupe, and `render_finding`; keep a small occurrence-baseline compare/write shim in the rule module (same as today's `_record_key` / `serialize_baseline` semantics).
  - From Codex-Innovation: Add a compatible baseline projection and serializer for this rule’s existing identity schema, then test loading and no-op rewriting a representative committed-schema baseline.
  - From Cursor-Pragmatic: Spell out the bridge explicitly: either (a) add a Piece 1 engine occurrence-row projection matching the existing keys and sort order, or (b) keep a thin rule-local baseline reader/writer for that schema while run_rule handles scan/suppression only. Do not assume generic or symbol-metric rows satisfy acceptance.
  - From Cursor-Pragmatic: Define the live-to-baseline projection in the plan: map findings to the existing four-field identity (or extend engine with that row shape) before comparison/write. Do not rely on generic line-based or symbol-metric projections alone.
  - From Codex-Pragmatic: Add a firm engine compatibility projection, parser, and writer for this existing markdown schema, then cover byte-stable no-op regeneration through the rule
  - From Cursor-Requirements: Pin an occurrence-key baseline projection in Approach (map live Finding to file/qualified_symbol/pattern_name/occurrence rows, preserve key order and sorting without sort_keys) and add a blocked-by Piece 1 dependency on that engine shape, or explicitly keep a thin rule-local baseline adapter while using run_rule scan-only until Piece 1 lands the third schema
  - From Codex-Requirements: Add a firm engine or rule-level compatibility projection that loads, compares, sorts, and writes the existing five-field schema byte-compatibly, then test it with a legacy-schema baseline
  - From Cursor-dyn-Lint Parity Auditor: Revise the plan: either extend Piece 1 engine with this occurrence-key shape, or keep a thin rule-local baseline bridge and use run_rule scan-only. Do not claim both unchanged baseline bytes and full run_rule baseline delegation.
  - From Cursor-dyn-Lint Parity Auditor: Preserve occurrence-key baseline semantics in the plan. If engine-backed, add a dedicated projection row type; do not map findings to generic path+line rows.
  - From Codex-dyn-Lint Parity Auditor: Add an engine baseline-row extension for this legacy identity, list `python/larch/lint/engine.py` and its tests in the plan, and use it for this rule.


### FINDING_5: The approximately 250-line production cap is incompatible with retained detector logic
- **Reviewer(s)**: Codex-Arch, Cursor-Innovation
- **Severity**: major
- **Concern**: Removing plumbing does not reduce the existing AST walker and symbol logic to the stated cap. The plan names no helper extraction.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Relax or remove the 250-line acceptance for this rule, or explicitly move shared AST helpers to a named module in a prior piece; do not treat boilerplate deletion alone as sufficient.
  - From Codex-Arch: Waive or renegotiate the line cap for this rule, or schedule helper extraction in an explicit dependency piece.


### FINDING_6: Mandatory equivalence harness updates are incorrectly optional
- **Reviewer(s)**: Cursor-Innovation, Codex-Arch, Codex-Pragmatic, Cursor-dyn-Lint Parity Auditor
- **Severity**: major
- **Concern**: The rewrite removes APIs used by the equivalence adapter, but the harness and fixture are marked optional. Git-backed discovery also requires tracked fixture files or an injected runner.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Promote `python/tests/lint/test_lint_engine_equivalence.py` (and its fixture if needed) to a firm `### UPDATED:` heading with an adapter that builds `SourceFile` values and calls `detect` directly.
  - From Codex-Arch: Elevate the equivalence test file to a firm `### UPDATED:` heading and switch the adapter to `SourceFile` + `detect`.
  - From Codex-Pragmatic: Make the equivalence test update a firm plan change; update the fixture only if its fields must change for the new adapter
  - From Cursor-dyn-Lint Parity Auditor: materialize_sources writes untracked files; legacy adapt_markdown_heading_fence_state uses iter_source_files rglob. Engine _discover_tracked_paths uses git ls-files --cached. Adapter replacement without git init or RecordingRunner returns zero findings and golden tests fail. Add an explicit plan step: init git, git-add fixture sources, or inject RecordingRunner listing tracked paths in adapt_markdown_heading_fence_state and equivalence cases.


### FINDING_8:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/larch/lint/engine.py:648-658, python/larch/lint/lint_markdown_heading_fence_state.py:32-68
- **Concern**: [SCOPE-REDUCTION] Plan routes baseline I/O through stock run_rule but engine supports only generic and symbol-metric rows. Scenario: Committed rows use {file, qualified_symbol, pattern_name, occurrence, reason}. engine._parse_baseline_row rejects that shape. Acceptance also requires a byte-identical no-op rewrite of python/markdown-heading-fence-state-baseline.json. A naive run_rule port cannot load, compare, or rewrite the committed baseline. Violates G-Enf-2 grandfathered-baseline contract.
- **Proposed resolution**: Call run_rule with baseline_path=None for discovery, detect, and suppression only. Keep a thin rule-local loader, writer, and comparator for the existing five-key schema (mirror current _record_key and serialize_baseline), or add an engine occurrence-key projection in a separate engine piece before this port. Do not claim run_rule owns baseline I/O until one of those exists.


### FINDING_9:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/larch/lint/engine.py:648-658
- **Concern**: [SCOPE-REDUCTION] run_rule baseline I/O cannot preserve the committed occurrence baseline schema. Scenario: Engine accepts only generic `{path,line,rule_id,message,reason}` or symbol-metric `{path,rule_id,qualified_symbol,metric,reason}` rows; markdown-heading-fence-state uses `{file,qualified_symbol,pattern_name,occurrence,reason}` with a 4-tuple identity that omits line numbers. Wiring `run_rule` baseline compare/write will reject the existing JSON, rewrite field names, and break the acceptance no-op byte-stable regen.
- **Proposed resolution**: Use engine discovery/source loading and `render_finding` only; keep a thin rule-local occurrence-baseline loader/writer keyed on `(file,qualified_symbol,pattern_name,occurrence)` around scan output, mirroring today's `_record_key`/`serialize_baseline` contract instead of `run_rule` baseline mode.


### FINDING_2: Baseline path-prefix mismatch
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: The committed baseline uses `python/`-relative `file` values while engine findings and selectors use repo-relative paths, so naive projection will fail matching and rewrite every row.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Specify codec mapping: serialize file as Finding.path removeprefix python/; parse baseline file back to Finding.path with python/ prefix; add round-trip and no-op regen tests.
  - From Cursor-Pragmatic: Add to the occurrence codec plan: `OccurrenceBaselineRow.path` is repo-relative (`python/<file>`) for engine filtering while JSON keeps python/-relative `file`; or pin check-mode `paths=None` and document why. Add a regression test mirroring `test_paths_outside_scope_are_excluded_even_when_tracked`.
  - From Cursor-Requirements: Specify in the occurrence codec that baseline file is Finding.path with a leading python/ stripped, and add a round-trip test from repo-relative Finding.path to baseline file and back.


### FINDING_5: Production scope must filter before source loading
- **Reviewer(s)**: Codex-Arch, Cursor-Pragmatic, Codex-Pragmatic, Codex-Requirements
- **Severity**: major
- **Concern**: Engine discovery and source loading can process tracked files that legacy production-scope filtering would exclude, including tests, support files, non-Python paths, and symlinks; malformed or unreadable excluded files can therefore cause false failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add rule-owned pre-load discovery scope, including Python pathspecs and safe exclusion of legacy paths and symlinks, for both check and write modes. Define the compatibility treatment for the existing pylint engine client and cover scoped write discovery with an injected runner.
  - From Cursor-Pragmatic: Document check/write `paths=` and discovery behavior in the REWRITTEN rule module plan (for example: `paths=["python"]` only with repo-relative occurrence row `.path`, or `paths=None` with detector-side production scope filtering and a test that untracked `test_*.py` fixtures stay excluded). Reuse `_git_ok_runner` patterns from `test_lint_pylint_skip_file.py`.
  - From Codex-Pragmatic: Name an engine-level pre-load path filter or rule pathspec/filter contract that excludes the legacy paths and symlinks before `_load_source` and `_scan_source`, and cover it through the rule main with the injected runner.
  - From Codex-Requirements: Add rule-level pre-load source selection or pathspec filtering for `python/**/*.py` plus legacy exclusions, and test that malformed excluded files do not affect check or write modes.


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


