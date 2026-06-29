### FINDING_1:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: plan.txt:28-31
- **Concern**: Parser only names two directive forms, so it misses unconditional Read clauses. Scenario: design/SKILL.md has direct always-loaded reads like `Read \`skills/design/references/readability-style.md\`` at lines 84 and 376. If the scanner only accepts `MANDATORY - READ ENTIRE FILE` and `Read ... completely`, the /design closure is undercounted and the baseline ratchet can silently miss real growth.
- **Proposed resolution**: Broaden clause harvesting to any unconditional markdown Read directive in SKILL.md, including bare backticked Read <path> lines, and add a regression test that pins the readability-style.md loads.

### FINDING_2:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:28-31
- **Concern**: Directive grammar is too narrow for current happy-path markdown loads. Scenario: The plan only recognizes `MANDATORY - READ ENTIRE FILE` and `Read ... .md completely`, but the target SKILLs also use `Read and apply ## ... in ...` and `MANDATORY — READ ENTIRE FILE` variants. The scanner would miss always-loaded refs such as `skills/design/SKILL.md:51`, undercount closure size, and weaken the growth ratchet.
- **Proposed resolution**: Broaden the parser to accept any mandatory-read clause that carries a markdown path in the read clause, regardless of dash punctuation or `and apply`/`completely` wording, and harvest only the path segment.
