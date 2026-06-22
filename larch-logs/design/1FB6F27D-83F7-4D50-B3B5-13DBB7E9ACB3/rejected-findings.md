### [Plan Review] FINDING_3

### FINDING_3: Registry inventory anchor missing for v2 key registry
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: Registry inventory anchor missing. Scenario: Plan asks for a v2 key registry but does not point implementers at the authoritative parse exclude set in `_dict_to_manifest` (`status`, `schema_version`, `skill`, `flags`, `operator_cwd`, `larch_version`, `model_roster`, `effort`, `attempt`, `superseded_by`, `stalled_at_step`, etc.). Omitting any of these reserved keys drops them on `from_json` and causes manifest byte drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add one plan bullet: seed the registry from the current `_dict_to_manifest` v2 exclude list plus merge-promotion rules in `_manifest_v2_merge`, and keep the planned registry parity test keyed to that full set.


### [Plan Review] FINDING_8

### FINDING_8: _count_findings parity unspecified when adopting parse_findings
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: `_count_findings` parity is unspecified when adopting `parse_findings`. Scenario: Today `_count_findings` increments on every `^### FINDING_[0-9]+:` line; `len(parse_findings(...))` counts blocks and ignores nested heading tokens inside a body, so accepted-count / FIX_COUNT / coder routing can change on the nested-heading fixture the plan already cares about for `_filter_in_scope`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Pin `_count_findings` to today's line-count semantics (dedicated heading-line helper or explicit test), or document and test that block-count replaces line-count only when nested in-body headings are absent.


### [Plan Review] FINDING_10

### FINDING_10:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/review_types.py:33-37 python/review_aggregate.py:246-248
- **Concern**: [SCOPE-REDUCTION] Finding.title is specified without a parse contract and callers today use raw blocks only. Scenario: Implementers may invent title parsing or ship a dead field; aggregate still derives IDs via _finding_id_from_block separately, adding churn without acceptance benefit
- **Proposed resolution**: Omit Finding.title from the frozen dataclass unless a caller needs it; document that parse_findings sets finding_id from the heading token and stores the raw heading line inside block


