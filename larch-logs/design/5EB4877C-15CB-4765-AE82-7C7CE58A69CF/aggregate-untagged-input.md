### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/larch/lint/lint_agent_tool_contract.py
- **Concern**: Plan pins violation output to stdout while tests and sibling lints use stderr. Scenario: The module section requires printing findings to stdout and tool failures to stderr, but the test section says to mirror python/tests/lint/test_lint_shared_convention_regex.py, and every lint pytest helper in that family asserts capsys.readouterr().err; lint_common.run_file_lint and lint_shared_convention_regex.main also emit violations on stderr. An implementer following the module text will fail the mirrored tests and diverge from the repo lint stream contract.
- **Proposed resolution**: Align the plan with sibling lints: print violations to stderr in the pinned path:line:message format, keep tool failures on stderr, and state explicitly that tests assert capsys.readouterr().err like test_lint_shared_convention_regex.py and test_lint_skill_invocations.py.

### FINDING_2:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/lint/lint_agent_tool_contract.py
- **Concern**: Suppression regex treats `<!-- lint-agent-tool-contract: ok -->` as valid. Scenario: The issue-specified pattern `<!--\s*lint-agent-tool-contract:\s*ok\s+(\S[^>]*?)\s*-->` matches `ok -->` with capture `--`, so matrix row 8 (missing-reason suppression should still find) can fail if tests use the natural `ok -->` pragma; operators may also think a bare `ok -->` comment suppresses the lint
- **Proposed resolution**: Tighten the plan regex to require at least one alphanumeric in the reason (for example `ok\s+(\S[^>]*[A-Za-z0-9][^>]*?)\s*-->`), or pin case-8 fixture text to a non-matching form such as `<!-- lint-agent-tool-contract: ok-->` / `ok` plus only whitespace before `-->`, and add one test asserting `ok -->` does not suppress ### 1. [correctness] `python/larch/lint/lint_agent_tool_contract.py` — Suppression regex treats `<!-- lint-agent-tool-contract: ok -->` as valid The plan copies the issue’s suppression regex `<!--\s*lint-agent-tool-contract:\s*ok\s+(\S[^>]*?)\s*-->`. For `<!-- lint-agent-tool-contract: ok -->`, the `\S` group can capture `--`, so the pragma counts as reason-bearing and matrix row 8 (“missing-reason suppression: finding”) fails if the fixture uses the obvious `ok -->` form. That also weakens G-Py-11 intent: a typo suppression could silence real violations. **Suggested revision:** Require at least one alphanumeric in the captured reason, or specify case-8’s exact non-matching pragma in the test plan and add a regression case proving `ok -->` does not suppress.

### FINDING_3:
- **Reviewer(s)**: Cursor-dyn-Lint Parser Contract
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/lint/lint_agent_tool_contract.py (planned)
- **Concern**: Finding line numbers must be repo-relative file lines, not body-relative matches. Scenario: Plan text says only "Use the first matching read-intent line number" and never requires adding `body_start_line` from the closing `---` fence. `lint_skill_invocations.extract_frontmatter_and_body` already computes this offset (`body_start_line = 2 + frontmatter_lines + 1` at ```21:36:python/larch/lint/lint_skill_invocations.py```) and `body_per_invocation_violations` reports `body_start_line + body_line_idx` (```157:168:python/larch/lint/lint_skill_invocations.py```). A body-relative index breaks the pinned `<path>:<line>:` contract and sends editors to the wrong line.
- **Proposed resolution**: Specify that read-intent hits are converted with the same `extract_frontmatter_and_body` offset before emission, or import that helper directly instead of re-deriving frontmatter split locally.

### FINDING_6:
- **Reviewer(s)**: Codex-dyn-Lint Parser Contract
- **Severity**: major
- **Focus area**: correctness
- **Location**: plan.txt:30-31
- **Concern**: Read-intent matcher misses the repo's common `READ ENTIRE FILE` instruction form used by reviewer agents.. Scenario: `agents/code-reviewer.md:14-15` and `agents/reviewer-correctness.md:13-15` use that exact wording; if one of those agents ever lost `Read`, the new lint would still pass and miss the contradiction.
- **Proposed resolution**: Add a pattern for bare `READ ENTIRE FILE` / `read entire file`, or widen the file-read regex so this phrasing is recognized.
