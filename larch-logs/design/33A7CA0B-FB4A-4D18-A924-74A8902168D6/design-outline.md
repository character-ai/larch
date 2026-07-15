## Proposed Design Outline

### Goals
- Rewrite `python/larch/lint/lint_unreachable_branch.py` (~820 lines) as a thin detector plus an engine-backed `LintRule`, at most ~250 lines.
- Preserve every detector behavior: control-flow analysis, fact invalidation, nested/async scopes, normalized-condition identities, occurrence handling, pragma and compatibility arguments.
- Keep `make lint-unreachable-branch`, `make test-lint-unreachable-branch`, and the equivalence cases green; leave `python/unreachable-branch-baseline.json` byte-unchanged on a no-op rewrite.

### Non-goals
- No detector behavior change: identical findings, identities, and rendered lines on the current tree.
- No edits to `engine.py`, the `("lint", "unreachable-branch")` entry in `python/larch/cli.py`, the Makefile targets, or the baseline path/schema.
- No new `argparse` CLI or baseline I/O in the module; the engine owns discovery, suppression, baseline, and output.

### Approach sketch
- Mirror the completed sibling port `python/larch/lint/lint_markdown_heading_fence_state.py` (124 lines) as the reference pattern.
- Keep the AST/control-flow detector as a `detect(SourceFile) -> Iterable[Finding]` function; delete argparse and baseline plumbing.
- Define one `LintRule` (`rule_id`, `pathspecs`, `detect`, `pragma_token` for back-compat) and a thin `main(argv)` that calls `run_rule`.
- Update `python/tests/lint/test_lint_unreachable_branch.py` to drive the engine-backed rule while keeping detector-focused cases.

### Surfaces in scope
- `python/larch/lint/lint_unreachable_branch.py` (rewrite)
- `python/tests/lint/test_lint_unreachable_branch.py` (update)
- Read-only reference: `python/larch/lint/engine.py`, `lint_markdown_heading_fence_state.py`, `python/tests/lint/test_lint_engine_equivalence.py`

### Open questions
- Confirm the current baseline shape and `pragma_token` map cleanly onto the engine loader (verified in principle by the sibling port; treat any true engine gap as an implement-time blocker, not scope creep).
