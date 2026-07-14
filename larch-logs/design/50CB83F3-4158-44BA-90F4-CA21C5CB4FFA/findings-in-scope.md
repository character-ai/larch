### FINDING_1: Existing test fixtures are not migrated for the hard gate
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Codex-Requirements
- **Severity**: major
- **Concern**: The baseline-free lint will continue failing on existing intentional `["gh", ...]` test literals because the plan names no deliverable to annotate or otherwise migrate the current fixture corpus.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add an explicit landing step or `### MAY_UPDATE:` batch for `python/tests/**` (and any other in-scope non-git modules) to apply reason-bearing same-line pragmas to every intentional existing `["gh", ...]` list literal before merge; keep the testing-strategy zero-finding check as verification, not the only mention of this work.
  - From Codex-Arch: Add the required `### UPDATED:` test files and same-line reason-bearing fixture pragmas for every retained test literal, then verify the final full-tree scan is clean
  - From Cursor-Innovation: Add an explicit landing deliverable (### MAY_UPDATE: bulk pragma migration or a mechanical sweep step) that annotates or rewrites every existing python/tests/** literal the rule matches, and gate merge on python3 python/cli.py lint gh-argv-literal returning 0 after production repoint.
  - From Codex-Requirements: Add firm updates for every intentional existing fixture literal with the required same-line pragma, or a plan-permitted explicit fixture allowlist.

### FINDING_2: Production pragmas can disable the hard ban
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Concern**: Allowing production literals to use the planned pragma lets violating code bypass the adoption lint, allowing enforcement to decay while CI remains green.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Permit pragma suppression only for explicit test-fixture paths or a reason-bearing fixture allowlist; reject production pragmas and replace the planned production-side suppression test with that rejection case

### FINDING_3: Lint discovery does not prune shared excluded directories
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Concern**: Recursive discovery may scan virtualenvs, vendored dependencies, or generated directories such as `.venv`, `node_modules`, `.agents`, and `__pycache__`, causing false findings or discovery failures and diverging from sibling linter behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: In lint_gh_argv_literal.py discovery, skip paths whose relative parts intersect the shared EXCLUDED_DIRS set from sibling lints (.git, node_modules, .venv, .agents, __pycache__ at minimum); keep tests/ and test_*.py in scope; document the vendored-dir skip in docs/linting.md; add one isolated-tree test that a python/.venv/*.py literal is not scanned

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/larch/lint/lint_gh_argv_literal.py
- **Concern**: [SCOPE-REDUCTION] Context-blind list-literal ban over-serves the adoption goal and forces needless test churn. Scenario: The issue targets reintroduction of raw gh argv construction in production callers, but the plan flags every ast.List whose first Constant is "gh" in every expression context. Most current hits are test assertion shapes like argv[:3] == ["gh", "issue", "create"] or helper calls that never bypass python/larch/git/gh.py at runtime; they cannot reintroduce divergent pagination or skip _retry_read. Enforcing them still requires a large same-line pragma surface (~100+ edits) unrelated to adoption decay, which is the opposite of minimum-change.
- **Proposed resolution**: Restrict findings to argv-construction contexts only (for example list literals passed as the first argument to proc.run/subprocess.run/Popen/check_output/call, plus ["gh", *...] splats fed into those calls). Keep tuple registry keys excluded. Add regression tests that Compare-context literals and ("gh", ...) tuples stay clean while real runner argv lists still report.

### FINDING_5:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/lint/lint_gh_argv_literal.py
- **Concern**: [SCOPE-REDUCTION] Production pragmas defeat the hard ban. Scenario: The plan explicitly permits and tests a production-side pragma, so a new raw production `["gh", ...]` argv can bypass the required ban with a comment.
- **Proposed resolution**: Restrict suppression to test fixtures under `python/tests/` or an explicit fixture allowlist, and remove production-side pragma support and coverage.
