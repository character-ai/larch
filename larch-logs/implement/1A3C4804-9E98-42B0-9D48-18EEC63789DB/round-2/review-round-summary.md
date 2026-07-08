# Review Round 2

- Mode: `diff`
- 3 accepted, 3 rejected (0 neutral)

## Accepted Findings

### FINDING_2: Preserve all failed jobs in capped digests
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-edge-cases
- **Severity**: major
- **Concern**: The digest applies a single global byte cap after assembling job sections, so one large early failure can crowd out later failed jobs. That violates the requirement that every failed CI job appear in the distilled output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.


### FINDING_3: Escape fence terminators in raw log excerpts
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: major
- **Concern**: Raw CI log text is emitted inside a fixed Markdown fence, so a branch-controlled log line containing triple backticks can terminate the fence and inject prompt-like text into the fixer context.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Address the concern above.


### FINDING_5: Include step labels in dedupe keys
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: major
- **Concern**: Dedupe keys that only use job family plus fingerprint can collapse distinct failing steps from the same job into one digest section, hiding a failure from the fixer.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Include the step label in the dedupe key, or restrict dedupe to exact step sections so only true shard duplicates merge.


