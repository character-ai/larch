### [Plan Review] FINDING_4

### FINDING_4: Sentinel not applied on BOTH_DOWN=false notice paths
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: Edge-case text claims the sentinel fires on `BOTH_DOWN=false` notice paths, but the procedure never says to touch it. On `BOTH_DOWN=false`, `AskUserQuestion` is skipped; on `/implement` dirty-tree or resume-plan-tail re-entry the gate re-runs and re-prints the explanation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: In the BOTH_DOWN=false sub-branch (and line 43), require the same sentinel check/touch before proceed; say re-warn/re-ask not only re-prompt


