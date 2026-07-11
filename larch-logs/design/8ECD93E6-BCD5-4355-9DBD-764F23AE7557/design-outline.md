## Proposed Design Outline

### Goals
- Extend `lint_lifecycle_prefix_literal` to flag lifecycle/bug tokens in composition positions (f-string, concat, `.format`), closing the writer gap behind #6935.
- Add a new `lint_prefix_case_variant` lint that bans case-variant bracketed tokens on prompt and residual-Bash surfaces, where `BUG_PREFIX` cannot be imported.
- Wire both lints into `make lint` so the shared-constant convention (G-Cfg-3) is enforced across code and prompt surfaces.

### Non-goals
- No change to `BUG_PREFIX` or the token model in `python/larch/issue/title_match.py`.
- No new writer surfaces and no rewrites of compliant writers; enforcement only.
- No grandfathered baseline for L2; the prompt/script scan is already clean.

### Approach sketch
- L1: add `fstring_compose`, `concat_compose`, `format_compose` to `CONTEXT_KINDS`, detecting via the existing casefolded `build_token_map` (equal token, or token followed by a space or colon).
- L1: keep the existing production-only scope, the `# lint-lifecycle-prefix: ok` pragma, and the reason-bearing baseline; migrate it with the documented `--write` flow (shrink-only, G-Enf-2).
- L2: new module shaped after `lint_shared_convention_regex`, scanning `skills/**`, `.claude/skills/**`, `agents/**`, and `residual-bash paths`; flag tokens that casefold-match a canonical token but differ in bytes.
- L2: Markdown suppression `<!-- lint-prefix-case-variant: ok <reason> -->`, Bash suppression `# lint-prefix-case-variant: ok <reason>`, non-empty reason required (G-Py-11); no baseline.
- Register `lint prefix-case-variant` in the `cli.py` lint table and add both checks to the standard sweep per `docs/linting.md`.

### Surfaces in scope
- `python/larch/lint/lint_lifecycle_prefix_literal.py`, `python/lifecycle-prefix-literal-baseline.json`
- `python/larch/lint/lint_prefix_case_variant.py` (new), `python/larch/cli.py`
- `python/tests/lint/test_lint_lifecycle_prefix_literal.py`, `python/tests/lint/test_lint_prefix_case_variant.py` (new)
- `docs/linting.md` and the `make lint` sweep wiring it names

### Open questions
- None. Names, context kinds, surfaces, suppression grammar, and baseline policy are fixed by the issue.
