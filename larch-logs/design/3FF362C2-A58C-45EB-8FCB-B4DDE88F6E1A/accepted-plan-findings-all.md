### FINDING_1: Self-review accepted count lacks durable tmpdir artifact
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: Accepted-count tracking is orchestrator mental state only with no durable tmpdir artifact. Replacing hardcoded `--accepted 0` with a counter the agent may forget or mis-increment reproduces the same non-uniform 0/0 vs real-count behavior seen in run logs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In Step 4 write a one-line durable artifact (for example `$IMPLEMENT_TMPDIR/self-review-accepted.count`) whenever an in-scope finding is fixed; before Step 9 reconcile the counter against that file and pass the reconciled integer literal into `write-self-review-tally`


### FINDING_2: docs/run-logs.md JSONL derivation rule conflicts with self-review tally path
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: Plan updates self-review tally semantics but does not require revising the general code-review counter paragraph that says `accepted_count` and `rejected_count` are derived from `review-findings-full.jsonl`. After landing, docs still claim JSONL is the counter source while self-review keeps JSONL empty and passes counts only via `write-self-review-tally` flags; log consumers and operators get contradictory contracts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: In the docs/run-logs.md edit, add an explicit self-review carve-out under code-review-tally.json stating counts come from CLI --accepted/--rejected at Step 5 and are not derived from review-findings-full.jsonl

**Merge note:** FINDING_1 targets SKILL.md orchestration durability (`skills/implement/SKILL.md:558-583`). FINDING_2 targets `docs/run-logs.md:317-322` documentation contract. Same severity, different surfaces and fixes; kept separate.


### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:558-583
- **Concern**: [SCOPE-REDUCTION] Accepted tally uses a mental `_self_review_accepted` counter with no durable artifact. Scenario: Issue scope requires deterministic self-review accounting; a forgotten or wrong mental count reproduces the 0/0 under-reporting class the bug fixes
- **Proposed resolution**: At Step 4 append one heading per applied in-scope finding to `$IMPLEMENT_TMPDIR/self-review-accepted.md`; before Step 9 count `###` self-review accepted headings (mirror rejected-findings.md) and substitute both integers into the tally fence



