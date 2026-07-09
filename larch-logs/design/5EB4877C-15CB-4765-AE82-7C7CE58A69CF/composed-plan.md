## Plan

## Scope

Implement the approved outline. `approach-synthesis.txt` is `NO_SKETCHES`, so this plan is based on direct repo inspection and the supplied feature text.

## Files to modify/create

### NEW: python/larch/lint/lint_agent_tool_contract.py

Create the lint module.

Key behavior:

- Scan only `agents/*.md` and `.claude/agents/*.md`, non-recursive.
- Skip files without a leading frontmatter block.
- Parse frontmatter manually with stdlib code.
- Treat no `tools:` key as clean.
- Treat scalar `tools:` values, such as `*` or `all`, as unrestricted and clean.
- Treat inline flow lists and block sequence lists as explicit restrictions.
- Flag an explicit empty or Read-less tool list only when the body contains read-intent language.
- Support this reason-required suppression anywhere in the file:
  `<!-- lint-agent-tool-contract: ok <reason> -->`
- Do not add a baseline path unless a genuine live-tree violation appears and cannot be fixed. The current plan expects no baseline.

Implementation shape:

- Start with a module docstring in sibling lint style.
- Mention the non-goal follow-up: machine-parsed-only output mandates without fail-closed language are possible future work, not part of v1.
- Define `TOOL_FAILURE_EXIT = 2`.
- Use a frozen `Finding` dataclass.
- Add module-level compiled regex constants for suppression and read-intent patterns.
- Keep one short comment per read-intent regex.
- Expose `main(argv: list[str] | None = None) -> int`.
- Return `0` clean, `1` findings, `2` usage or tool failure.
- Print findings as:
  `<path>:<line>: agent declares tools without Read but its prompt instructs reading files; add Read, drop the instruction, or suppress with lint-agent-tool-contract: ok <reason>`
- Print tool failures to stderr.

Parser notes:

- Normalize CRLF to LF and strip a UTF-8 BOM.
- Frontmatter is the block between a leading `---` line and the next `---` line.
- Body starts after the closing frontmatter fence.
- Recognize only top-level `tools:` with no leading whitespace.
- Inline list parsing should handle `tools: []`, `tools: [Read]`, `tools: [Read, Grep]`, and quoted tokens.
- Block sequence parsing should handle:
  `tools:` followed by indented `- Name` lines until the next non-list line.
- If an inline list is malformed, treat it as a tool failure, not clean.
- If a block list item is malformed, treat it as a tool failure.
- Use the first matching read-intent line number for the finding.

### UPDATED: python/larch/cli.py

Add the lint registry row near the other lint rows:

`("lint", "agent-tool-contract"): ("larch.lint.lint_agent_tool_contract", "main"),`

Keep the existing registry style and ordering.

### UPDATED: Makefile

Add `agent-tool-contract` to the `py-lint-checks-fast` loop list.

Do not add a separate harness target unless the surrounding Makefile convention requires it for new lint tests.

### NEW: python/tests/lint/test_lint_agent_tool_contract.py

Add pytest coverage that mirrors `python/tests/lint/test_lint_shared_convention_regex.py` in fixture style.

Cover the full required matrix:

1. `tools: []` plus read-intent sentence: finding.
2. `tools: [Grep]` plus read-intent sentence: finding.
3. `tools: [Read]` plus read-intent sentence: clean.
4. Block sequence containing `- Read` plus read-intent sentence: clean.
5. No `tools:` key plus read-intent sentence: clean.
6. `tools: []` plus no read-intent language: clean.
7. `tools: []` plus read-intent sentence plus reason-bearing suppression: clean.
8. `tools: []` plus read-intent sentence plus missing-reason suppression: finding.
9. Scalar `tools: *` plus read-intent sentence: clean.

Also add a live-tree test that runs `main(["--root", <repo root>])` and expects exit `0` with no findings.

Test details:

- Build temporary trees with `agents/` and `.claude/agents/` fixtures.
- Assert exit codes and captured output.
- Include at least one case for each read-intent regex family:
  read files, open file or bundle, and use `Read`.
- Include a malformed frontmatter or malformed list case only if it keeps the test small and useful.

### UPDATED: ARCHITECTURAL_INVARIANTS.md

Append the exact Deliverable B block.

Placement:

- Add a new `## Agent contracts` section after `## Run-log integrity`.
- Keep one blank line between the existing final paragraph and the new heading.
- Keep `### I-Agent-1:` byte-identical to the feature text.

### UPDATED: ARCHITECTURAL_GUIDELINES.md

Append two exact guideline blocks.

Placement:

- Add `### G-Orch-6:` inside `## Orchestration and panels`, immediately after `### G-Orch-5` and before `## Observability and telemetry`.
- Add `### G-Ext-3:` inside `## External tools`, immediately after `### G-Ext-2` and before `## Documentation and Markdown`.
- Keep both blocks byte-identical to the feature text.

### UPDATED: docs/linting.md

Document the new lint in the existing per-lint style.

Add:

- What it flags.
- Scan surface: `agents/*.md` and `.claude/agents/*.md`.
- Explicit pass cases for no `tools:`, scalar `tools:`, `Read` present, and toolless agents with no read intent.
- Suppression pragma with required reason.
- No-baseline policy.
- Test location.
- `python3 python/cli.py lint agent-tool-contract`.

## Approach

1. Implement the parser and scanner first.
2. Add tests for parsing and detection before wiring the Makefile.
3. Wire the CLI registry.
4. Wire `make py-lint`.
5. Append the invariant and guideline text exactly.
6. Add linting docs.
7. Run the focused checks.

## Edge cases

- Empty inline list must count as explicit restriction.
- Missing `tools:` must not count as restriction.
- Scalar wildcard must not count as restriction.
- A malformed suppression without reason must not suppress.
- Body scanning must ignore frontmatter.
- A read-intent phrase in comments still counts unless suppressed.
- The current live tree should stay clean, including generated reviewer agents and `.claude/agents/bug-fix-triage.md`.

## Failure modes

- Over-broad read-intent regex can create live-tree false positives.
- Under-broad regex can miss the required fixture cases.
- YAML parsing drift can misclassify scalar versus explicit list.
- Output stream and format can drift from tests. Pin the exact finding message.
- Docs blocks can fail byte-identity checks if rewrapped or “improved.”
- `make py-lint` can omit the check if only the CLI row is added.

## Testing strategy

Run focused checks only:

- `python3 python/cli.py lint agent-tool-contract`
- `python3 -m pytest python/tests/lint/test_lint_agent_tool_contract.py -q`
- `make py-lint`

Also verify no baseline file was added and no existing agent definition file changed.

## Acceptance mapping

- Criteria 1 and 2: new lint and tests.
- Criteria 3: Makefile loop.
- Criteria 4 and 5: exact Markdown appends.
- Criteria 6: `docs/linting.md`.
- Criteria 7: no agent file edits.
- Criteria 8: focused local checks.

confidence: high

## Acceptance

Run focused checks only:

- `python3 python/cli.py lint agent-tool-contract`
- `python3 -m pytest python/tests/lint/test_lint_agent_tool_contract.py -q`
- `make py-lint`

Also verify no baseline file was added and no existing agent definition file changed.

review_status: complete
rounds_completed: 1
difficulty: MODERATE
diff_lines: 430
