## Goal
Implement issue #6672: [IMPLEMENTING] [BUG] Heading-grammar drift persists after #6632: coverage indexer and core reader regexes diverge on depth and area charset; single-source the grammar and lint the class.

## Implementation Plan
## Plan

Context:
- `approach-synthesis` is `NO_SKETCHES`; draft from direct repo inspection and the provided scope.
- `discussion-round1` resolves the key choices: reader grammar is canonical, the new lint covers both ID-heading and `[BUG]` predicate conventions, and no grandfathered baseline lands.
- The approved outline has no open questions.

Approach:
1. Promote the reader regexes in `python/larch/core/architectural_guidelines.py` to public constants:
   - `GUIDELINE_HEADING_RE = re.compile(..., re.MULTILINE)`
   - `INVARIANT_HEADING_RE = re.compile(..., re.MULTILINE)`
2. Update `parse_guideline_entries` and `parse_invariant_entries` to use those constants. Keep behavior unchanged:
   - guidelines: exactly `###`
   - invariants: `#` through `######`
   - `INV-*`: rejected
3. Repoint `learn_from_bugs.coverage_index()` to the shared constants. Delete the duplicate local ID regexes.
4. **Unconditionally** route `DEFAULT_SEARCH` through `title_match.BUG_PREFIX` so the production constant cannot drift from the shared bug-title predicate:
   - `from larch.issue.title_match import BUG_PREFIX`
   - `DEFAULT_SEARCH: Final = f"{BUG_PREFIX} in:title"`
   - Preserve the exact query value (`"[BUG] in:title"`).
5. Add `lint_shared_convention_regex` as a hard-ban lint:
   - scan production `python/larch/**/*.py`
   - exclude `python/tests/`, test helpers, owner modules, the lint implementation module, and irrelevant prose/docstrings
   - same-line suppression: `# lint-shared-convention-regex: ok <reason>`
   - explicit owner allowlist:
     - `larch/core/architectural_guidelines.py`
     - `larch/issue/title_match.py`
   - flag duplicate guideline/invariant heading regex shapes outside the architectural-guidelines owner
   - flag duplicate `[BUG]` title-selector literals in **module-level** `Assign` / `AnnAssign` string constants outside the title-match owner (e.g. `"... in:title"` containing the bug prefix)
   - defer `Call` / `Compare` / `re.compile` `[BUG]` positions to `lint_lifecycle_prefix_literal` to avoid double-reporting
   - avoid double-reporting simple lifecycle-prefix contexts already owned by `lint_lifecycle_prefix_literal`
6. Wire the lint into `python/cli.py lint shared-convention-regex` and `make py-lint-checks-fast`.
7. Add regression tests for reader/indexer parity and lint behavior.

Files to modify/create:

### UPDATED: python/larch/core/architectural_guidelines.py
- Rename `_HEADING_RE` to `GUIDELINE_HEADING_RE`.
- Rename `_INVARIANT_HEADING_RE` to `INVARIANT_HEADING_RE`.
- Add `re.MULTILINE` to both compiled constants.
- Keep the regex bodies equal to the current reader grammar.
- Update parser call sites to use the public constants.

### UPDATED: python/larch/issue/learn_from_bugs.py
- Import `GUIDELINE_HEADING_RE` and `INVARIANT_HEADING_RE` from `larch.core.architectural_guidelines`.
- Import `BUG_PREFIX` from `larch.issue.title_match`.
- Delete `_GUIDELINE_ID_RE` and `_INVARIANT_ID_RE`.
- Pass the shared constants to `_scan_marked_ids`.
- **Required:** set `DEFAULT_SEARCH: Final = f"{BUG_PREFIX} in:title"` (no conditional rewrite wording; no raw `"[BUG]"` literal remains in this module).

### NEW: python/larch/lint/lint_shared_convention_regex.py
- Implement a focused AST/token-based lint with exit codes `0` clean, `1` violations, `2` tool failure.
- Reuse local patterns from nearby lint modules where practical:
  - sorted production file discovery
  - normalized repo-relative paths
  - pragma parsing with required reason
  - stable violation messages
- Add an explicit owner allowlist mirroring lifecycle lint:
  - `ALLOWLIST_RELPATHS = frozenset({"larch/core/architectural_guidelines.py", "larch/issue/title_match.py"})`
  - exclude `larch/lint/lint_shared_convention_regex.py` from production scan scope when detector fragments embed heuristic convention shapes
- Keep it hard-ban only. Do not add a committed baseline.
- Heading-convention detection:
  - flag duplicate guideline/invariant ID-heading regex shapes outside the architectural-guidelines owner
  - include module-level regex constants and `re.compile(...)` calls in scope
- Bug-title selector detection:
  - flag module-level `Assign` / `AnnAssign` string constants whose value contains a `[BUG]` title-selector pattern (for example `"... in:title"`)
  - **do not** flag `Call` / `Compare` / `re.compile` `[BUG]` positions; those remain owned by `lint_lifecycle_prefix_literal`
- Ensure the lint does not self-report its detector code. Prefer detector fragments that do not themselves encode the full protected convention.
- Report clear owner guidance, for example:
  - use `architectural_guidelines.GUIDELINE_HEADING_RE`
  - use `architectural_guidelines.INVARIANT_HEADING_RE`
  - use `title_match.bug_title_match` or `title_match.BUG_PREFIX`

### UPDATED: python/larch/cli.py
- Register `("lint", "shared-convention-regex")` to the new lint module.

### UPDATED: Makefile
- Add `$(PYTHON) python/cli.py lint shared-convention-regex` to `py-lint-checks-fast`.
- Place it near the other Python AST ratchets (after `lifecycle-prefix-literal`).

### UPDATED: python/tests/issue/test_learn_from_bugs.py
- Replace the narrow invariant-only parity parametrization with one cross-module fixture test that exercises both architectural files from a single synthetic fixture.
- Include in one fixture file:
  - `G-*` headings at depths 1 through 6
  - a hyphenated guideline area (for example `G-Run-Log-1`)
  - `I-*` headings at depths 1 through 6
  - an `INV-*` heading
  - a mid-line `G-Xx-1:` prose reference
- Add a small test helper that derives the reader-accepted `(id, title)` population from parser output, not from first-line string equality:
  - run `parse_guideline_entries` / `parse_invariant_entries` on the fixture text
  - split the normalized output into entry blocks on blank lines
  - for each block, parse the first heading line with a stable `^###\s+(G-[A-Za-z0-9-]+-\d+):\s*(.+?)\s*$` / `^###\s+(I-[A-Za-z0-9-]+-\d+):\s*(.+?)\s*$` extractor (or reuse the shared constants on the normalized heading line) to build `reader_guidelines` and `reader_invariants` tuples
- **Primary parity assertion (triple equality):** for each architectural file, build expected populations from the shared constants:
  - `expected_guidelines = tuple((m.group(1), m.group(2)) for m in GUIDELINE_HEADING_RE.finditer(text))`
  - `expected_invariants = tuple((m.group(1), m.group(2)) for m in INVARIANT_HEADING_RE.finditer(text))`
  - assert `coverage_index(...).guidelines == expected_guidelines`
  - assert `coverage_index(...).invariants == expected_invariants`
  - assert `reader_guidelines == expected_guidelines`
  - assert `reader_invariants == expected_invariants`
- This closes the accepted gap: the test must fail if reader preprocessing or matcher choice diverges from shared-constant scanning even when indexer output still matches constants.
- Keep rejected-heading checks as secondary guards only:
  - `INV-*` absent from both reader and indexer populations
  - mid-line `G-Xx-1:` absent from both populations
  - depth-2 / depth-4 `G-*` headings absent from both populations
- Add a fixture or assertion that current committed architectural files still parse/index identically under the triple-equality contract.
- Add an assertion that `DEFAULT_SEARCH == f"{BUG_PREFIX} in:title"`.

### NEW: python/tests/lint/test_lint_shared_convention_regex.py
- Cover:
  - a violating duplicate ID-heading regex
  - a violating module-level `Assign` / `AnnAssign` `[BUG]` selector literal (for example `DEFAULT_SEARCH = "[BUG] in:title"`)
  - a clean fixture that imports shared constants/helpers
  - a same-line suppression with a reason
  - missing suppression reason fails
  - owner modules (`architectural_guidelines.py`, `title_match.py`) are skipped via allowlist
  - the lint implementation module is excluded from scan scope
  - lifecycle-prefix `Call` / `Compare` / `re.compile` contexts already owned by `lint_lifecycle_prefix_literal` are not double-reported
- Add a scope test mirroring `test_lint_lifecycle_prefix_literal.py` owner/test/helper exclusion behavior.

### UPDATED: docs/linting.md
- Document `python/cli.py lint shared-convention-regex`.
- State the protected owners, the module-level `[BUG]` selector surface, and the same-line suppression format.

Edge cases:
- `re.MULTILINE` must not affect parser behavior because parser inputs are split into single lines before `.match()`.
- `finditer()` over whole files must now use the same compiled regex as the reader.
- A depth-3 `G-*` heading with a hyphenated area must be indexed and read.
- Depth-2 or depth-4 `G-*` headings must be rejected by both.
- Depth-1, depth-5, and depth-6 `I-*` headings must be accepted by both.
- `INV-*` must stay rejected by both.
- Mid-line references like prose containing `G-Xx-1:` must stay rejected.
- `DEFAULT_SEARCH` must remain byte-identical to today's implicit default while sourcing `BUG_PREFIX`.
- Module-level bug-search constants are in scope for the new lint; comparison/match/`re.compile` bug-prefix uses remain lifecycle-lint-owned.
- Reader population extraction must use the full parser output population, not `splitlines()[0:1]` smoke checks, so a reader that silently drops accepted headings still fails parity.

Failure modes:
- A broad lint can create noisy false positives in docstrings, comments, or display text. Keep detection tied to selector-like string and regex contexts; exclude display strings and docstrings for bug-prefix module constants the same way lifecycle lint excludes non-match surfaces.
- A narrow lint can miss the next duplicate parser. Include module-level regex constants, `re.compile` calls, and module-level string constants in scope.
- The new lint can self-report if its detector literals look like protected grammars. Use the owner allowlist and exclude the lint module from scan scope.
- Importing from `larch.core` into `larch.issue` should pass layering, but verify with the existing layering lint.
- Splitting bug-prefix ownership between lifecycle lint (match/compare/regex contexts) and shared-convention lint (module-level constants) can miss or double-report if boundaries drift; keep the division explicit in both lints' tests.
- A parity test that asserts only indexer-vs-constant equality can still pass when reader preprocessing diverges; the triple-equality contract prevents that false green.

Testing strategy:
- Run focused unit tests:
  - `python3 -m pytest python/tests/issue/test_learn_from_bugs.py python/tests/lint/test_lint_shared_convention_regex.py`
- Run focused lint checks:
  - `python3 python/cli.py lint shared-convention-regex`
  - `python3 python/cli.py lint lifecycle-prefix-literal`
  - `python3 python/cli.py lint layering`
- Run `make py-lint` if time permits, since the new lint is wired into that target.
- Do not update `SECURITY.md`; this is convention parsing and lint enforcement, not secret or permission behavior.

confidence: high

## Acceptance

See Testing strategy in plan.

diff_added: 420
diff_deleted: 30
mechanical_churn: false
diff_lines: 465

## Test plan
(no test plan section in plan-file)
