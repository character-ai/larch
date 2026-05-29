### FINDING_1: Dedup doc overstates fenced-region protection
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Codex-Innovation, Codex-Pragmatic
- **Severity**: latent
- **Concern**: The proposed authoritative dedup documentation says fenced regions are protected, but the existing byte-stable behavior still collapses duplicate lines inside fenced blocks. This could mislead future maintainers into changing the helper to preserve duplicate fenced lines, contradicting current tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch, Codex-Arch: Revise the divergence note to say dedup recognizes any fenced region for heading/Constraints state while still applying duplicate-line collapse inside fences; keep the existing fenced-duplicate assertions unchanged.
  - From Cursor-Innovation, Codex-Innovation: Reword the note: the balanced fence model prevents headings inside matched fences from changing Constraints state; duplicate lines inside fences still dedup
  - From Codex-Pragmatic: Revise the planned doc wording to say the balanced fence model suppresses heading and Constraints state inside matched fences, while duplicate-line collapse still applies inside fences; keep the parser-divergence cross-reference

### FINDING_2: agent-lint exclusion must be unconditional for variableized helper caller
- **Reviewer(s)**: Cursor-dyn-lint-graph-coverage, Codex-dyn-lint-graph-coverage
- **Severity**: important
- **Concern**: The agent-lint exclusion is conditional even though the proposed runtime caller uses shell variable indirection. Since agent-lint 2.3.2 does not follow that indirection, relevant-checks may fail on the new helper despite a real runtime caller.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-lint-graph-coverage, Codex-dyn-lint-graph-coverage: Make the agent-lint.toml update unconditional and name the exact placement: add skills/design/scripts/dedup-plan-lines.py with a short caller comment matching the variable-indirection style, and add skills/design/scripts/dedup-plan-lines.md to the existing skill-local sibling .md exclusion block or beside the helper if keeping the sibling with its helper entry.
