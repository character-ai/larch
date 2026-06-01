### [Plan Review] FINDING_6

### FINDING_6: Fork-aware remote selection beyond cited bash ports
- **Reviewer(s)**: Cursor-Edge
- **Severity**: nit
- **Concern**: `push.py` adds fork-aware origin vs upstream remote selection. `scripts/git-push.sh` and `create-pr.sh` use default/origin push only; extra remote logic is scope beyond the cited port and risks drift unless rebase-push rules are required.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Port git push behavior only (tracking remote/refspec); defer fork remote resolution to Phase 7 driver unless a cited bash caller needs it


