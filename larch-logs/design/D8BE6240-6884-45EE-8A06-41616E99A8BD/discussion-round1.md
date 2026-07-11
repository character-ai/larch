# Discussion Round 1

## Decision 1: Matching backward compatibility
- **Question**: Should larch keep recognizing pre-existing mixed-case `[Bug]` issues/comments (case-insensitive) for dedup and bug-mining, while only emitting canonical `[BUG]`?
- **Resolution**: Yes. Generation emits canonical `[BUG]`; matchers and the cross-repo dedup regex continue to accept both `[Bug]` and `[BUG]` so historical comments still dedup and bug-mining still sees old issues.
- **Source**: user

## Decision 2: Canonicalization scope
- **Question**: How wide should canonicalization reach beyond the filed-issue title generators?
- **Resolution**: All source-side `[Bug]` literals: the `_report.py` terminal/escalation title generators, the design chat-fallback header (`design_terminal.py:737`), the dedup-regex consumer, and test fixtures that assert generated output. Leave `[Bug]`-as-*input* tests (case-insensitive matcher coverage in `test_learn_from_bugs.py`, `test_analyze_bugs.py`, and the lint-rule detector tests) unchanged.
- **Source**: user

## Hard constraints
- `larch-logs/` is off-limits (historical run-log artifacts) — no edits there.
- The case-insensitive `bug_title_match` predicate and its input-based tests must keep passing.
- The lint rule `lint_lifecycle_prefix_literal.py` flags any `[BUG]`/`[Bug]` string literal in source; generation sites must use `title_match.BUG_PREFIX`, not a bare `[BUG]` literal.
