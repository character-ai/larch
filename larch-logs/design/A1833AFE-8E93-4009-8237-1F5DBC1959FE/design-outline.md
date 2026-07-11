## Proposed Design Outline

### Goals
- Adopt the learn-from-bugs residuals for issue #6873: six guideline entries, the `I-Commit-1` invariant, and three lint scaffolds.
- Each work item passes its own stated acceptance check.
- Graduate `I-Gate-1` from a human-readable invariant to an enforced check via lint 3b.

### Non-goals
- Do not wire the new lints into required CI status checks. The merge gate stays local `make lint`, `make py-lint`, and the pre-commit hook.
- Do not change any existing guideline or invariant entry. Text blocks are pasted verbatim.
- Do not implement the commit-time `larch-logs/` scan that `I-Commit-1` describes as its mechanical backing. Work item 2 only appends the invariant text.

### Approach sketch
- Append the six guideline blocks after their named siblings (`G-Wire-2`, `G-Ext-3`, `G-Md-2`, `G-CLI-2`, `G-IO-2`, `G-Obs-5`), and `I-Commit-1` after `I-Flush-1` under `## Run-log integrity`.
- Scaffold three lint modules mirroring `lint_tempfile_dir.py`, each with a `SUPPRESSION` constant, `main(argv) -> int`, argparse `prog="cli.py lint <name>"`, a matching test, a `cli.py` dispatch row, `make lint-<name>` and `make test-lint-<name>` targets, and pre-commit plus `py-lint-checks-fast` wiring.
- Run each lint on the current tree to pick hard-ban versus shrinking baseline per its stated policy. `unreachable-branch` always ships with a baseline; the other two hard-ban only if zero violations.

### Surfaces in scope
- `ARCHITECTURAL_GUIDELINES.md`, `ARCHITECTURAL_INVARIANTS.md`
- `python/larch/lint/lint_markdown_heading_fence_state.py`, `lint_self_disarmable_gate.py`, `lint_unreachable_branch.py`
- `python/tests/lint/test_lint_markdown_heading_fence_state.py`, `test_lint_self_disarmable_gate.py`, `test_lint_unreachable_branch.py`
- `python/larch/cli.py` dispatch table, `Makefile`, `docs/linting.md`
- `python/<lint>-baseline.json` baselines, conditional per scan results

### Open questions
- None. The issue is a paste-ready spec; baseline policy is implementation-time.
