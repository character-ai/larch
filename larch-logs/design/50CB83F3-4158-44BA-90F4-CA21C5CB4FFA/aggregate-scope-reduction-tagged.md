### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/larch/lint/lint_gh_argv_literal.py
- **Concern**: [SCOPE-REDUCTION] Context-blind list-literal ban over-serves the adoption goal and forces needless test churn. Scenario: The issue targets reintroduction of raw gh argv construction in production callers, but the plan flags every ast.List whose first Constant is "gh" in every expression context. Most current hits are test assertion shapes like argv[:3] == ["gh", "issue", "create"] or helper calls that never bypass python/larch/git/gh.py at runtime; they cannot reintroduce divergent pagination or skip _retry_read. Enforcing them still requires a large same-line pragma surface (~100+ edits) unrelated to adoption decay, which is the opposite of minimum-change.
- **Proposed resolution**: Restrict findings to argv-construction contexts only (for example list literals passed as the first argument to proc.run/subprocess.run/Popen/check_output/call, plus ["gh", *...] splats fed into those calls). Keep tuple registry keys excluded. Add regression tests that Compare-context literals and ("gh", ...) tuples stay clean while real runner argv lists still report.

### FINDING_7:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/lint/lint_gh_argv_literal.py
- **Concern**: [SCOPE-REDUCTION] Production pragmas defeat the hard ban. Scenario: The plan explicitly permits and tests a production-side pragma, so a new raw production `["gh", ...]` argv can bypass the required ban with a comment.
- **Proposed resolution**: Restrict suppression to test fixtures under `python/tests/` or an explicit fixture allowlist, and remove production-side pragma support and coverage.
