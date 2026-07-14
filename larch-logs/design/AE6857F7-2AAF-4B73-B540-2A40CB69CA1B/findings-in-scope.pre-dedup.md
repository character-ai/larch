### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/rendering/_rendering_generators.py:1-2
- **Concern**: Module-preamble detection must cover skip-file after a module docstring. Scenario: The plan tests spacing variants of `skip-file` but not docstring-first layouts. `_rendering_generators.py` puts `# pylint: skip-file` on line 2 after a line-1 docstring. A preamble rule that only scans before the first physical line, or that stops at the docstring, would miss a baselined grandfathered module or emit the wrong line identity.
- **Proposed resolution**: Add an explicit module-preamble contract (all unindented `#` comments before the first `import`/`from`/statement, regardless of docstring position) and a test fixture mirroring `_rendering_generators.py` docstring-then-skip-file ordering.



### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/lint/engine.py:287-320
- **Concern**: Unreadable-file edge case conflicts with unchanged engine exit semantics. Scenario: Edge cases require unreadable tracked files to fail closed "with findings," but `engine._load_source` raises `ScanError` and `run_rule` returns exit `2` with stderr only. The plan also forbids changing engine validation, discovery, baseline comparison, and exit codes.
- **Proposed resolution**: Align edge cases and tests with engine behavior: unreadable paths exit `2` without a stdout finding; reserve exit `1` for live detections such as malformed Python under `syntax_policy=fail`.



### FINDING_3:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/lint/duplicate_code.py:242-249; python/tests/lint/test_duplicate_code.py:259-270
- **Concern**: The planned exclusion of local or block-level disables leaves a live R0801 bypass. Scenario: Pylint processes every comment token as a module-scope pragma; the existing block-level test proves a post-header `disable=duplicate-code` suppresses duplicate-code findings. An indented equivalent can therefore evade the new gate.
- **Proposed resolution**: Detect R0801 and duplicate-code disables wherever Pylint applies them, regardless of indentation or position, and add a fixture proving such a directive is rejected.



### FINDING_4:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/lint/lint_pylint_skip_file.py
- **Concern**: Module-level parser must accept space-separated pylint disable forms. Scenario: The plan requires comma-separated value parsing and skip-file spacing tests, but only lists disable=R0801 / disable=duplicate-code variants. Pylint also accepts `# pylint: disable R0801` and `# pylint: disable duplicate-code` without `=`. A detector keyed on `=` forms leaves a working whole-file duplicate-code bypass in python/larch/.
- **Proposed resolution**: Specify and test both `disable=<codes>` and `disable <codes>` module-preamble grammars for R0801 and duplicate-code, including comma-separated tails in each form.



### FINDING_5:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: python/larch/lint/engine.py
- **Concern**: [SCOPE-REDUCTION] Drop unreadable-file exit-1 edge case. Scenario: Edge cases require unreadable tracked files to surface findings with exit 1, but engine.py discovery calls `_load_source`, which raises `ScanError` and `run_rule` returns exit 2 before the rule detector runs. The engine update explicitly keeps discovery and exit codes unchanged, so this edge case cannot be met without new engine behavior.
- **Proposed resolution**: Remove unreadable-file exit-1 language from Edge cases and tests, or document that unreadable paths remain engine exit 2 while malformed Python stays syntax_policy exit 1.



