---LARCH-REJECTED-BEGIN---
## Considered Plan Review Suggestions (Not Adopted)

These reviewer suggestions were considered but not adopted. Some may already be addressed by the current plan; they are not automatically unimplemented gaps.

### [Plan Review] FINDING_2

### FINDING_2: Suppression pragma can accept an empty-looking reason
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Concern**: The suppression regex can treat `<!-- lint-agent-tool-contract: ok -->` as reason-bearing, so a bare or nearly bare pragma could incorrectly suppress findings and weaken the intended no-bare-pragma rule.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Tighten the plan regex to require at least one alphanumeric in the reason (for example `ok\s+(\S[^>]*[A-Za-z0-9][^>]*?)\s*-->`), or pin case-8 fixture text to a non-matching form such as `<!-- lint-agent-tool-contract: ok-->` / `ok` plus only whitespace before `-->`, and add one test asserting `ok -->` does not suppress ### 1. [correctness] `python/larch/lint/lint_agent_tool_contract.py` — Suppression regex treats `<!-- lint-agent-tool-contract: ok -->` as valid The plan copies the issue’s suppression regex `<!--\s*lint-agent-tool-contract:\s*ok\s+(\S[^>]*?)\s*-->`. For `<!-- lint-agent-tool-contract: ok -->`, the `\S` group can capture `--`, so the pragma counts as reason-bearing and matrix row 8 (“missing-reason suppression: finding”) fails if the fixture uses the obvious `ok -->` form. That also weakens G-Py-11 intent: a typo suppression could silence real violations. **Suggested revision:** Require at least one alphanumeric in the captured reason, or specify case-8’s exact non-matching pragma in the test plan and add a regression case proving `ok -->` does not suppress.


### [Plan Review] FINDING_3

### FINDING_3: Finding lines need the frontmatter-to-body offset
- **Reviewer(s)**: Cursor-dyn-Lint Parser Contract
- **Severity**: major
- **Concern**: The plan does not clearly require converting read-intent matches into repo-relative file line numbers. If it uses body-relative positions directly, emitted findings can point to the wrong line and violate the pinned `<path>:<line>:` contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-Lint Parser Contract: Specify that read-intent hits are converted with the same `extract_frontmatter_and_body` offset before emission, or import that helper directly instead of re-deriving frontmatter split locally.


### [Plan Review] FINDING_4

### FINDING_4: Read-intent detection misses common bare-file instruction wording
- **Reviewer(s)**: Codex-dyn-Lint Parser Contract
- **Severity**: major
- **Concern**: The read-intent matcher as described may miss the repo’s common `READ ENTIRE FILE` wording. That would let an agent instruction still pass the lint even though it clearly requires file reading.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-Lint Parser Contract: Add a pattern for bare `READ ENTIRE FILE` / `read entire file`, or widen the file-read regex so this phrasing is recognized.


### [Plan Review] FINDING_5

### FINDING_5:
- **Reviewer(s)**: Cursor-dyn-Lint Parser Contract
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/lint/lint_agent_tool_contract.py (planned); python/tests/lint/test_lint_agent_tool_contract.py (planned)
- **Concern**: [SCOPE-REDUCTION] Violation output stream drifts from every sibling lint and from the mirrored test harness. Scenario: Plan module text prints findings with bare `print(...)` and reserves stderr for tool failures only, while `lint_common.run_file_lint` prints violations on stderr (```108:111:python/larch/lint/lint_common.py```), `lint_shared_convention_regex.main` prints findings on stderr (```236:240:python/larch/lint/lint_shared_convention_regex.py```), and the plan's own test model `test_lint_shared_convention_regex.run` captures `capsys.readouterr().err` (```16:18:python/tests/lint/test_lint_shared_convention_regex.py```). Mixed streams make the new lint behave unlike `lint skill-invocations` / `lint skill-description-length` and invite a green test that asserts the wrong stream.
- **Proposed resolution**: Print violations to stderr like `lint_common` / `lint_shared_convention_regex`; keep stderr for tool failures; assert `.err` in tests (or call `lint_common.run_file_lint` and only custom-parse `tools:`).


### [Plan Review] FINDING_6

### FINDING_6:
- **Reviewer(s)**: Cursor-dyn-Lint Parser Contract
- **Severity**: minor
- **Focus area**: code-quality
- **Location**: python/larch/lint/lint_agent_tool_contract.py (planned)
- **Concern**: [SCOPE-REDUCTION] Plan re-specifies frontmatter/BOM/CRLF parsing already owned by `lint_skill_invocations`. Scenario: Feature scope asks to reuse sibling frontmatter approach when importable; `extract_frontmatter_and_body` in ```21:36:python/larch/lint/lint_skill_invocations.py``` already normalizes BOM/CRLF and returns `(frontmatter, body, body_start_line)`. A third copy raises drift risk against `lint_skill_description_length.extract_frontmatter` (```17:28:python/larch/lint/lint_skill_description_length.py```) without adding rule surface.
- **Proposed resolution**: Import `extract_frontmatter_and_body` for split/offset; keep only `tools:`-specific parsing local (inline flow + block sequence can still mirror `_parse_allowed_tools_tokens` / block walk in the same module). ## 1. correctness — planned `lint_agent_tool_contract.py` Finding line numbers must be absolute file lines. The plan never binds read-intent matches to `body_start_line`, but `lint_skill_invocations.extract_frontmatter_and_body` and `body_per_invocation_violations` already define the correct offset math. Without that, `<path>:<line>:` points at the wrong row even when detection is right. **Suggested revision:** Import `extract_frontmatter_and_body` (or document the identical offset formula) and add `body_start_line + body_line_idx` before printing. ## 2. correctness — planned lint module + tests Violation output should go to stderr. Sibling lints and the mirrored `test_lint_shared_convention_regex` harness all use stderr for findings; the plan’s stdout/stderr split is the outlier. **Suggested revision:** Emit findings on stderr; assert `capsys.readouterr().err` in tests (or wrap with `lint_common.run_file_lint`). ## 3. code-quality — planned `lint_agent_tool_contract.py` Reuse `extract_frontmatter_and_body` instead of a third hand-rolled frontmatter parser. That cuts duplicate BOM/CRLF logic and aligns with the feature’s “reuse sibling approach” note. **Suggested revision:** Import the helper from `lint_skill_invocations`; keep only `tools:` list parsing local. --- **Live-tree scan (no finding):** Fifteen `agents/*.md` and `.claude/agents/*.md` files match the planned non-recursive globs. Agents with explicit tool lists all include `Read`; tool-less implementer agents (`cursor-implementer.md`, `codex-implementer.md`, `_implementer-base.md`) have no `tools:` key and their “read the output” / “Read this template” prose does not match the planned determiner+noun read-intent families. `bug-fix-triage.md` already has `tools: [Read]` with read-intent body text. A live-tree exit-0 test is appropriate. **Fixture matrix (no finding):** The nine mandatory cases plus per-regex-family coverage and suppression with/without reason match the feature spec; optional malformed-list testing is correctly left optional in the plan. **Makefile / CLI wiring (no finding):** `py-lint-checks-fast` loop at ```57:58:Makefile``` is the correct insertion point; CLI rows live in the `("lint", ...)` table in `python/larch/cli.py` near ```420:452:python/larch/cli.py```.


---LARCH-REJECTED-END---
