### [rejected] FINDING_1

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_1: suppression markers match non-comment text
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: important
- **Concern**: Suppression scanning can trigger on marker text inside string literals or other non-comment text, so a real em-dash violation can disappear or a benign string can raise a false suppression-format error.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Parse suppressions only from trailing # comments or AST comment nodes not from string literal substrings.
  - From cursor-specialist-correctness: Limit empty-reason checks to comment tails or ignore matches inside string literals.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** dismissed (0 YES)

### FINDING_4: fenced output examples are skipped
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-lint-scope
- **Severity**: important
- **Concern**: Fenced blocks are skipped wholesale, so canonical output examples inside skill/reference docs are never checked and can still carry em-dash separators.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Update the fenced example to colon separators to match SKILL.md
  - From cursor-specialist-edge-cases: Refresh examples to colon separators consistent with the new convention
  - From cursor-specialist-testing: Update examples to colon form or add non-fenced lint coverage if examples are treated as canonical output.
  - From dyn-dyn-lint-scope: Inside fences, still scan lines matching the `Print:`/`print \`...\`` and line-leading `⏩` output patterns (or require unfenced `Print:`/`⏩` lines for canonical output specs and migrate fenced examples to colon form).


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

