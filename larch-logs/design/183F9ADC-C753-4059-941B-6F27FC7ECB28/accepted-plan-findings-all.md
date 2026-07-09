### FINDING_1: Make `DEFAULT_SEARCH` unconditional
- **Reviewer(s)**: Codex-Arch, Cursor-Innovation
- **Severity**: major
- **Concern**: `learn_from_bugs.py` still keeps the `[BUG]` search literal hardcoded behind conditional rewrite language, which leaves the production constant mismatched with the shared bug-title predicate and risks lint failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Make the rewrite mandatory, for example `DEFAULT_SEARCH = f"{BUG_PREFIX} in:title"`, and remove the conditional wording
  - From Cursor-Innovation: In learn_from_bugs.py import BUG_PREFIX from title_match and set DEFAULT_SEARCH to f"{BUG_PREFIX} in:title" (or equivalent) as a required step not an optional lint-driven follow-up


### FINDING_3: Use shared heading populations for the cross-module parity test
- **Reviewer(s)**: Cursor-Innovation, Cursor-dyn-Regex Ratchet Reviewer
- **Severity**: minor
- **Concern**: The parity test should compare the actual `(id, title)` populations accepted by the shared heading regexes, not parser-normalized prose strings or only first-line shapes, or it can miss drift across depths and formats.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: In the new fixture assert coverage_index().guidelines and .invariants equal tuple((m.group(1) m.group(2)) for m in GUIDELINE_HEADING_RE.finditer(text)) and the invariant constant finditer respectively; keep parse_* assertions only as secondary checks that rejected headings stay absent
  - From Cursor-dyn-Regex Ratchet Reviewer: Build expected reader tuples by applying the shared `GUIDELINE_HEADING_RE`/`INVARIANT_HEADING_RE` `.finditer()` to the fixture (same path `_scan_marked_ids` uses), or parse `(id, title)` from the first normalized heading line; assert set equality with `coverage_index()` for both files.


### FINDING_4: Cover module-level string constants in the hard-ban lint
- **Reviewer(s)**: Cursor-dyn-Regex Ratchet Reviewer
- **Severity**: major
- **Concern**: The hard-ban lint must detect module-level `Assign`/`AnnAssign` string constants containing the `[BUG]` title-selector pattern, not just the lifecycle-style `Call`/`Compare` surfaces.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-Regex Ratchet Reviewer: Extend the new lint AST walk to flag module-level `Assign`/`AnnAssign` string constants whose value contains a `[BUG]` title-selector (e.g. `"... in:title"`), while deferring Call/Compare/`re.compile` `[BUG]` positions to `lint_lifecycle_prefix_literal` to avoid double-report.


### FINDING_5: Add an owner-module allowlist to the hard-ban scan
- **Reviewer(s)**: Cursor-dyn-Regex Ratchet Reviewer
- **Severity**: major
- **Concern**: The scan needs an explicit allowlist for the canonical owner modules, or it will flag the source of truth for the convention and fail CI by linting its own definitions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-Regex Ratchet Reviewer: Mirror lifecycle lint: add `ALLOWLIST_RELPATHS = frozenset({"larch/core/architectural_guidelines.py", "larch/issue/title_match.py"})` (and exclude `larch/lint/lint_shared_convention_regex.py` if the detector embeds heuristic fragments). Add a scope test like `test_lint_lifecycle_prefix_literal.py:110-131`.


### FINDING_3: Parity test still omits reader-accepted population assertion
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Concern**: The regression test can still pass even if the reader and indexer diverge on preprocessing or matcher choice, because it does not explicitly assert the reader-accepted `(id, title)` population.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: For the same fixture, derive the reader (id, title) population from parse_guideline_entries and parse_invariant_entries output and assert it equals the expected shared-constant population and coverage_index output.

