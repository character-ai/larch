---LARCH-REJECTED-BEGIN---
## Considered Plan Review Suggestions (Not Adopted)

These reviewer suggestions were considered but not adopted. Some may already be addressed by the current plan; they are not automatically unimplemented gaps.

### [Plan Review] FINDING_1

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


### [Plan Review] FINDING_3

### FINDING_3: Existing main tests lack the git Runner contract
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Concern**: Existing `tmp_path` tests invoke `main()` without a git repository or injected Runner, but the engine-backed implementation requires git discovery before baseline behavior can be tested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Mirror lint_pylint_skip_file tests: reuse _git_ok_runner/_write_files from test_lint_engine.py, monkeypatch proc.ProcRunner in every main() test, and assert check/write/stale/malformed-python exit codes through the injected runner.


### [Plan Review] FINDING_4

### FINDING_4: Thin adapter does not pin run_rule scope and stale behavior
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: major
- **Concern**: The adapter must explicitly preserve legacy check/write discovery and strict stale-row exit behavior; unspecified `run_rule` arguments can change scope and exit codes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Document in the REWRITTEN rule module: check uses paths=["python"] and strict_stale=True; write uses paths=None with rule discovery pathspecs python; keep --root/--write/--initial-reason mapping; add one main() test per exit path.
  - From Cursor-Innovation: In the thin adapter, call `run_rule` like `lint_pylint_skip_file`: `paths=["python"]` for check mode, `paths=None` only for `--write`, and `strict_stale=not write_baseline`; keep production filtering inside `detect`.


### [Plan Review] FINDING_6

### FINDING_6: No explicit occurrence baseline projection dispatch
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Concern**: Generic `_project_finding` rejects the rule’s `qualified_symbol`/missing-`metric` shape, and `run_rule` has no explicit occurrence-codec dispatch surface for parsing, projecting, comparing, and publishing occurrence rows.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add an explicit `LintRule` baseline-dispatch field and branch `_parse_baseline_row`, `_project_findings`, `_baseline_comparison`, `_rows_for_write`, and `_publish_baseline` through that hook for occurrence rows only.


### [Plan Review] FINDING_7

### FINDING_7: Serializer does not preserve legacy baseline bytes
- **Reviewer(s)**: Cursor-Innovation, Cursor-Requirements
- **Severity**: major
- **Concern**: The generic serializer changes key names, key order, sorting, or formatting, so a no-op rewrite would not remain byte-identical to the committed legacy baseline.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Give the occurrence codec its own serializer: `file` key (python/-relative), legacy tuple sort, `indent=2`, no `sort_keys`, trailing newline; keep read-back validation against that format.
  - From Cursor-Requirements: Define the occurrence codec serializer to match legacy markdown output exactly: indent=2, no sort_keys, file/qualified_symbol/pattern_name/occurrence/reason field order, trailing newline; cover with the planned byte-identical rewrite test.


---LARCH-REJECTED-END---
