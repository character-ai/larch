# Review Round 1

- Mode: `diff`
- 1 accepted, 1 rejected (0 neutral)

## Accepted Findings

### FINDING_1: timing allow-list misses argparse defaults
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing
- **Severity**: major
- **Concern**: The timing allow-list harness still misses argparse `default=` literals and other static task-kind fallbacks for `--timing-task-kind`, so a new runtime kind can pass `make test-design-structure` and only warn at runtime.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Add parser.add_argument("--timing-task-kind", default="new-kind") in python/larch/agents/_drafter.py; make test-design-structure stays green while runtime emits only timing: WARNING: unknown task-kind: new-kind. Extend AST scanning for add_argument default= strings and quoted or-fallback task kinds, or centralize literals; add a harness negative fixture.
  - From codex-specialist-correctness: Extend the AST scan to inspect `ast.Call` nodes for `add_argument("--timing-task-kind", default="<literal>")`, and record the literal default when it is non-empty and not dynamic.
  - From cursor-specialist-edge-cases: Extend assert_timing_task_kind_allowlist() to collect string defaults from add_argument AST calls and fail on kinds missing from TIMING_TASK_KINDS_ALLOWED; add a regression fixture for default-only literals.
  - From codex-specialist-edge-cases: Visit ast.Call add_argument nodes, match --timing-task-kind, and record string-literal default values
  - From cursor-specialist-testing: Extend AST scanning to capture add_argument default strings, add a negative harness fixture, and reconcile against python/cli.py timing task-kinds.
  - From codex-specialist-testing: Extend AST scanning to record literal default values from argparse add_argument calls and add regression coverage


