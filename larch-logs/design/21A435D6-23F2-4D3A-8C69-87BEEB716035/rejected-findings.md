### [Plan Review] FINDING_1

### FINDING_1: Broaden always-loaded markdown read directive parsing
- **Reviewer(s)**: Codex-Pragmatic, Codex-Requirements
- **Severity**: blocking
- **Concern**: The planned closure scanner recognizes too few directive forms. It can miss unconditional markdown reads that are already present in the target SKILL files, including bare backticked `Read <path>` lines, `Read and apply ... in ...` clauses, and mandatory-read variants with different dash punctuation. That undercounts `/design` or `/implement` closure size and weakens the baseline ratchet.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Broaden clause harvesting to any unconditional markdown Read directive in SKILL.md, including bare backticked Read <path> lines, and add a regression test that pins the readability-style.md loads.
  - From Codex-Requirements: Broaden the parser to accept any mandatory-read clause that carries a markdown path in the read clause, regardless of dash punctuation or `and apply`/`completely` wording, and harvest only the path segment.

