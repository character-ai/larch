### FINDING_1: Occurrence baseline codec is incompatible
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Codex-Innovation, Codex-Requirements, Cursor-dyn-Control Flow Parity, Codex-dyn-Control Flow Parity
- **Severity**: major
- **Concern**: The engine occurrence-baseline codec supports `pattern_name`, while the unreachable-branch baseline requires `normalized_condition`. The plan forbids both the required engine change and rule-local baseline bridge, so non-empty baselines cannot be loaded or rewritten byte-stably.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Name the Piece 1 engine deliverable: load/write occurrence rows with normalized_condition (alias or dedicated codec), or revise Approach to run_rule scan-only plus a thin rule-local baseline comparator/writer that preserves the five-key schema; drop the contradictory no-engine/no-local-baseline pair
  - From Codex-Arch: Make Piece 1’s exact legacy normalized_condition occurrence codec and its regression test an explicit prerequisite before approving this rewrite, then configure this rule against that codec
  - From Cursor-Innovation: Add an explicit upstream deliverable: MAY_UPDATE engine.py to parse/serialize normalized_condition occurrence rows (or accept both keys with identical identity), with tests in test_lint_engine.py; or re-scope this piece to scan-only run_rule plus a thin rule-local baseline bridge until that codec lands.
  - From Codex-Innovation: Keep this plan blocked until Piece 1 provides a normalized_condition-compatible occurrence codec, then name that compatible dependency contract in the plan.
  - From Codex-Requirements: Do not approve this port until Piece 1 provides a schema-preserving normalized_condition occurrence codec. Name that resolved engine contract in the plan, or keep this piece blocked.
  - From Cursor-dyn-Control Flow Parity: Add an explicit blocked-by deliverable (firm engine.py update or named Piece 1 extension) that loads and writes the exact legacy keys including normalized_condition with stable field order, or revise acceptance if migrating the JSON field to pattern_name.
  - From Codex-dyn-Control Flow Parity: Make the required normalized_condition occurrence-schema support an explicit satisfied Piece 1 dependency before this port, then name the compatible engine contract in the plan.


### FINDING_4: Production discovery scope is not pinned
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Requirements, Cursor-dyn-Control Flow Parity
- **Severity**: major
- **Concern**: Reusing the markdown rule’s repository-wide Python pathspecs could scan files outside `python/larch`, changing legacy behavior and baseline results.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Pin pathspecs to python/larch/*.py and python/larch/**/*.py plus a source_filter mirroring is_exempt_path/EXCLUDED_DIRS; document that production discovery is git-tracked under that subtree only
  - From Cursor-Innovation: Pin LintRule pathspecs (and any source_filter) to python/larch/**/*.py with the same test/support/symlink exclusions as today; add a test that python/cli.py or python/bootstrap.py under python/ but outside larch is not scanned.
  - From Cursor-Requirements: Set LintRule.pathspecs to python/larch/*.py and python/larch/**/*.py (or equivalent) and keep the existing test/support/symlink exclusions. Do not reuse markdown's repo-wide python/** pathspecs.
  - From Cursor-dyn-Control Flow Parity: Pin LintRule pathspecs to python/larch/**/*.py (or equivalent) and state that production scope must remain the larch subtree only.


### FINDING_5: Suppression can change occurrence identities
- **Reviewer(s)**: Cursor-Arch, Codex-Pragmatic, Cursor-Requirements, Cursor-dyn-Control Flow Parity
- **Severity**: major
- **Concern**: Engine-level post-detection suppression can consume occurrence numbers for suppressed findings, changing per-function baseline identities and golden outputs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Keep pragma gating inside detect before occurrence assignment; treat engine suppression_token as empty-reason enforcement only, and state that explicitly in Approach/Edge cases
  - From Codex-Pragmatic: Keep legacy occurrence assignment semantics, and add a case with a suppressed matching branch before a live matching branch that asserts the live finding remains occurrence 1.
  - From Cursor-Requirements: Keep pragma evaluation inside the scanner before occurrence assignment, set allow_inline_suppression=False on RULE, and let engine own syntax_policy plus shared pragma grammar only (same split as markdown heading fence).
  - From Cursor-dyn-Control Flow Parity: Keep suppression and empty-reason ScanError in the detector, set allow_inline_suppression=False on LintRule, and finalize occurrence numbering after suppressed hits are dropped.


### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/lint/lint_unreachable_branch.py:93-104
- **Concern**: [SCOPE-REDUCTION] Plan does not pin discovery to python/larch only. Scenario: Today `_collect_all` walks only `root/python/larch` via `iter_source_files`. The markdown port uses engine pathspecs `python/**/*.py`, which would scan all tracked Python under `python/`, not just `larch/`. That can surface new findings outside the current scope and fail byte-stable acceptance.
- **Proposed resolution**: In Approach or the REWRITTEN bullets, set `LintRule.pathspecs` to `python/larch/**/*.py` (or an equivalent `source_filter` that requires `python/larch/`). Do not reuse markdown's whole-tree pathspecs.


### FINDING_1: Occurrence-baseline identity fields are not pinned
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: major
- **Concern**: The detector adaptation does not explicitly populate the required occurrence-baseline identity fields. With `occurrence_baseline=True`, each finding must carry `qualified_symbol`, `pattern_name`, and `occurrence`; a message-only adapter fails engine validation before baseline comparison.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: In detect(), set pattern_name to the normalized condition string, occurrence to the per-qualified-symbol index, and qualified_symbol to the legacy value; keep the existing message format. Add a test that adapted findings pass engine validation and round-trip through the Piece 1 normalized_condition codec.
  - From Cursor-Pragmatic: In `detect()`, emit engine `Finding` values with `qualified_symbol`, `occurrence`, and `pattern_name=<normalized_condition>`; keep the existing rendered message/cond text unchanged.


### FINDING_3: Production discovery does not preserve legacy exclusions
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: The proposed pathspecs alone still discover tracked test, support, and other legacy-excluded files under `python/larch`, widening scan scope and potentially changing findings or baseline identities.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add a repo-relative pre-load filter on `RULE` (reuse the existing `is_exempt_path` / excluded-dir predicate scoped to `python/larch/...`) and keep the planned CLI test that `python/cli.py` stays out of scope.
  - From Cursor-Requirements: In the REWRITTEN `LintRule`, add a pre-load `source_filter` matching legacy exclusions (reuse or narrow `is_production_source_path` / `is_exempt_path`). Extend production CLI discovery tests to assert tracked `test_*.py` and support files under `python/larch` are not scanned.


### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/lint/lint_unreachable_branch.py
- **Concern**: [SCOPE-REDUCTION] Production exclusion filter is unspecified for git discovery. Scenario: Pathspecs python/larch/**/*.py still match tracked test_*.py, conftest.py, and support filenames under python/larch. Legacy iter_source_files drops them via is_exempt_path; engine discovery uses git ls-files plus optional source_filter. The plan says to preserve exclusions but does not wire a LintRule source_filter (markdown uses is_production_source_path). A tracked exempt file would be scanned and could change live identities and baseline results.
- **Proposed resolution**: Reuse the existing is_exempt_path logic as a repo-relative source_filter on LintRule, mirroring lint_markdown_heading_fence_state.py. Extend the engine-backed CLI test to git-track an exempt filename and assert it is skipped while eligible python/larch files are scanned.

