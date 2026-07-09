### FINDING_2: Renderer baseline seeding and name matching miss `_vendor_rows`
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-Lint Ratchet Reviewer
- **Severity**: major
- **Concern**: The current seeding plan omits `larch/report/tokens.py` `_vendor_rows`, and the planned test-reference check uses plain name text matching, which can falsely treat `_progress_vendor_rows` as coverage for `_vendor_rows`. That lets an unreferenced `*_rows` helper stay unratcheted while `make py-lint` still passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add `larch/report/tokens.py` `_vendor_rows` to the seed inventory, or drop the static inventory and require seeding only through `make regen-renderer-golden-tests-baseline` after the lint is implemented
  - From Cursor-Pragmatic: Add `tokens.py` `_vendor_rows` to the candidate list, or replace the explicit enumeration with a single rule: seed only via `make regen-renderer-golden-tests-baseline` after the lint exists.
  - From Cursor-Requirements: Define test-reference matching as whole-identifier tokens (for example regex `\b<name>\b` or an AST/token scan of test sources), not bare substring search. Re-measure during seeding and include `larch/report/tokens.py` / `_vendor_rows` in the baseline (or add an explicit test reference) so `make py-lint` matches the live predicate set.
  - From Cursor-dyn-Lint Ratchet Reviewer: In lint_renderer_golden_tests.py, match test references with identifier boundaries (for example re.search with `(?<![A-Za-z0-9_])name(?![A-Za-z0-9_])`), not bare `name in text`. Add a test_lint_renderer_golden_tests.py case where only `_progress_vendor_rows` appears in fixtures and `_vendor_rows` still fails. Re-measure and seed python/renderer-golden-tests-baseline.json with 14 rows, including tokens._vendor_rows.


