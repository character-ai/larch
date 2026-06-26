## Decision 1: Threshold policy for dynamic reviewer failures
- **Question**: Should a dropped/failed dynamic reviewer be able to fail the panel threshold, or only ever warn?
- **Resolution**: Full parity. Dynamic reviewers count identically to static ones in INTENDED/SUCCEEDED/FAILED/COUNTED and can fail the panel threshold.
- **Source**: user

## Decision 2: Log preservation scope
- **Question**: Should preserving per-reviewer launch stderr/sidecars for dropped/straggler reviewers into larch-logs/ be in scope?
- **Resolution**: In scope. No separate issue exists for this item.
- **Source**: user
