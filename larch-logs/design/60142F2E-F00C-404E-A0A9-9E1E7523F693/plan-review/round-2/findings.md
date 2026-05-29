### FINDING_1:
- **Reviewer(s)**: Cursor-Arch, Codex-Arch
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/design/scripts/dedup-plan-lines.md:1; skills/design/scripts/test-plan-review-loop.sh:1768-1769
- **Concern**: The proposed authoritative doc says dedup protects any fenced region, but the existing byte-stable behavior and tests collapse duplicate lines inside fenced blocks.. Scenario: Future maintainers may read the new contract as requiring fenced duplicate preservation and change the helper away from the current behavior.
- **Proposed resolution**: Revise the divergence note to say dedup recognizes any fenced region for heading/Constraints state while still applying duplicate-line collapse inside fences; keep the existing fenced-duplicate assertions unchanged.

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation, Codex-Innovation
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/design/scripts/dedup-plan-lines.md (proposed; plan.txt:16)
- **Concern**: Proposed doc says dedup protects any fenced region, but the moved code still collapses duplicate lines inside fences; current tests assert fenced_count and tagged_fenced_count are 1 at skills/design/scripts/test-plan-review-loop.sh:1762-1769. Scenario: Future maintainer may treat fenced content as protected and change behavior, violating the byte-identical refactor contract
- **Proposed resolution**: Reword the note: the balanced fence model prevents headings inside matched fences from changing Constraints state; duplicate lines inside fences still dedup

### FINDING_3:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/design/scripts/plan-review-loop.sh:563-576; skills/design/scripts/test-plan-review-loop.sh:1768-1769
- **Concern**: Planned dedup doc says dedup protects any fenced region, but the byte-identical code still collapses adjacent duplicate lines inside matched fences. Scenario: The new dedup-plan-lines.md becomes the authoritative contract and can mislead future edits into preserving duplicate fenced lines, contradicting existing tests that expect fenced duplicates to collapse
- **Proposed resolution**: Revise the planned doc wording to say the balanced fence model suppresses heading and Constraints state inside matched fences, while duplicate-line collapse still applies inside fences; keep the parser-divergence cross-reference

### FINDING_4:
- **Reviewer(s)**: Cursor-dyn-lint-graph-coverage, Codex-dyn-lint-graph-coverage
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:33-34; skills/design/scripts/plan-review-loop.sh:21-23; agent-lint.toml:458-463
- **Concern**: agent-lint exclusion is conditional even though the proposed caller is variableized. Scenario: agent-lint 2.3.2 does not follow shell variable indirection, and the plan adds DEDUP_PLAN_LINES_PY plus a python3 "$DEDUP_PLAN_LINES_PY" call, so skipping the exclusion can make relevant-checks fail on the new helper despite a real runtime caller
- **Proposed resolution**: Make the agent-lint.toml update unconditional and name the exact placement: add skills/design/scripts/dedup-plan-lines.py with a short caller comment matching the variable-indirection style, and add skills/design/scripts/dedup-plan-lines.md to the existing skill-local sibling .md exclusion block or beside the helper if keeping the sibling with its helper entry.
