### FINDING_1: [OUT_OF_SCOPE] architectural-file read-policy split
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: `_scan_marked_ids` still reads architectural files with `errors="replace"` and without `_validate_architectural_file` symlink/containment checks, while `read_guidelines` / `read_invariants` reject symlinks and invalid UTF-8 strictly. That read-policy split predates this branch, but it remains a residual path where the coverage index could count headings the design reader never surfaces.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Reuse the reader’s validation/read helper (or call `_validate_architectural_file` and match its UTF-8 policy) inside `_scan_marked_ids` so dedup indexing and drafting see the same file population.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

### FINDING_2: [OUT_OF_SCOPE] heading-regex heuristic false negatives
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-convention-lint
- **Severity**: minor
- **Concern**: Heading duplicate detection is still heuristic, so equivalent regex spellings and call shapes can bypass the hard-ban lint.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: If this class recurs, tighten heuristics (canonical-shape compare against owner patterns) or add a small baseline for known-safe false-positive shapes rather than relying on substring checks alone.
  - From cursor-specialist-testing: Also treat [0-9] digit classes as numeric markers in the heuristics and add a violating fixture that must exit 1.
  - From dyn-dyn-convention-lint: Compare against normalized forms of the owner patterns (or compile-and-compare against `GUIDELINE_HEADING_RE.pattern` / `INVARIANT_HEADING_RE.pattern`) instead of checking for `\d` and `\s` substrings, and add regression fixtures for `[0-9]` and literal-space variants.


Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_3: [OUT_OF_SCOPE] module-level `[BUG] in:title` construction bypasses the lint
- **Reviewer(s)**: cursor-specialist-edge-cases, codex-specialist-edge-cases, dyn-dyn-convention-lint
- **Severity**: major
- **Concern**: The `[BUG] in:title` guard only handles plain constant RHS values, so equivalent selectors built with joins, concatenation, or f-string construction can still evade the lint.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Document that boundary in `docs/linting.md` (partially done) and extend AST coverage to class-body `AnnAssign` if a duplicate appears there; `f"-string` composition is already the intended escape hatch and is used correctly in `learn_from_bugs.py`.
  - From codex-specialist-edge-cases: Fold string-only JoinedStr and BinOp(Add) expressions, or inspect the source segment, and add regression tests for f-string and concatenation forms.
  - From dyn-dyn-convention-lint: Extend bug-selector detection to cover `ast.BinOp`/`ast.JoinedStr` module-level RHS forms when they fold to a constant containing both `BUG_PREFIX` (or `"[BUG]"`) and `"in:title"`, or reject any module-level search constant that contains `"in:title"` unless it is exactly `f"{BUG_PREFIX} in:title"` built from `title_match.BUG_PREFIX`.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_4: [OUT_OF_SCOPE] pragma suppression test fidelity
- **Reviewer(s)**: codex-specialist-testing, cursor-specialist-plan-fidelity-auto
- **Severity**: minor
- **Concern**: The pragma test only checks that a mixed fixture exits 1, so it does not prove the reason-bearing suppression is honored.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Address the concern above.
  - From cursor-specialist-plan-fidelity-auto: Address the concern above.


Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=false

