### [Plan Review] FINDING_9

### FINDING_9: Ledger row field extraction lacks a concrete shared contract
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The plan says to take title, file_line, and reason from ballot blocks but names no helper. Ad-hoc parsing will produce inconsistent rows and weaken cross-round duplicate matching.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Plan says to take title/file_line/reason from ballot blocks but names no helper. Ad-hoc parsing will produce inconsistent rows and weak cross-round duplicate matching (the feature goal). Add a small shared extractor (e.g. heading title from `### FINDING_N:` / `### OOS_N:`, first backtick `path:line` token, one-line reason from Concern/body) reused by both tally call sites; unit-test it in `test_findings_ledger.py`.


### [Plan Review] FINDING_10

### FINDING_10: v2 auto-suppression deferred despite scope requiring near-exact rejected duplicate drop
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: The approved outline defers v2 embedding auto-suppression, but scope requires near-exact rejected duplicates to be dropped before the ballot. Without `review aggregate-findings` ledger comparison, round-2+ can still raise rejected duplicates and consume voting tokens; the changed-location guard is also missing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add the aggregate-findings ledger comparison for rejected and neutral near-exact same-file-line duplicates with the intervening-change guard, plus the specified v2 tests.


