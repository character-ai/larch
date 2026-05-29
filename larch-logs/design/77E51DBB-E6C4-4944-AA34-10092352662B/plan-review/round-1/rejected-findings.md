### [Plan Review] FINDING_5

### FINDING_5: Edit-in-sync contract omits new trailers and output keys
- **Reviewer(s)**: Cursor-dyn-doc-sync, Codex-dyn-doc-sync
- **Severity**: important
- **Concern**: The plan keeps the existing `check-plan-size.md` Edit-in-sync list instead of explicitly adding the new optional input trailers and emitted machine-output keys, leaving future updates prone to contract drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-doc-sync: Replace "Keep the existing" with an explicit Edit-in-sync expansion: name the three optional input trailers and four machine-output keys, and add `skills/design/references/approval-gates.md` (Gate B Step 2b.5 summary at :161) to the file list
  - From Codex-dyn-doc-sync: Revise the check-plan-size.md plan item so Edit in sync explicitly mentions optional trailer grammar and emitted-key contract changes, including DIFF_ADDED, DIFF_DELETED, MECHANICAL_CHURN, and SOFT_ADVISORY

