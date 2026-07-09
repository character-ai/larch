## Proposed Design Outline

### Goals
- Add `lint_agent_tool_contract` to catch agent definitions that declare a restricted tool list without `Read` but instruct file reading in the prompt body.
- Document the prevention as invariant I-Agent-1, guideline G-Ext-3, and guideline G-Orch-6 in the repo knowledge files.
- Wire the new lint into `make py-lint` and cover it with a mandatory test matrix.

### Non-goals
- Do not modify any existing agent definition file.
- Do not lint skill files, hooks, or external-agent prompts.
- Do not implement the advisory second check (machine-parsed-only output without fail-closed clause).

### Approach sketch
- Create `python/larch/lint/lint_agent_tool_contract.py`: stdlib frontmatter parser, compiled read-intent regexes, suppression pragma, `main(argv) -> int`, exit-code contract mirroring `lint_shared_convention_regex.py`.
- Register in `python/larch/cli.py` lint dispatch table and add to the `for chk in ...` loop in `Makefile`.
- Create `python/tests/lint/test_lint_agent_tool_contract.py` covering all 9 fixture cases plus the live-tree zero-finding check.
- Append I-Agent-1 to `ARCHITECTURAL_INVARIANTS.md` under a new `## Agent contracts` section.
- Append G-Ext-3 inside `## External tools` and G-Orch-6 inside `## Orchestration and panels` in `ARCHITECTURAL_GUIDELINES.md`.
- Add a per-lint section in `docs/linting.md`.

### Surfaces in scope
- `python/larch/lint/lint_agent_tool_contract.py` (new)
- `python/tests/lint/test_lint_agent_tool_contract.py` (new)
- `python/larch/cli.py`
- `Makefile`
- `ARCHITECTURAL_INVARIANTS.md`
- `ARCHITECTURAL_GUIDELINES.md`
- `docs/linting.md`

### Open questions
- None.
