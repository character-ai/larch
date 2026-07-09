## Decision 1: Flush-time label check scope
- **Question**: Should the flush-time label check for I-Outcome-1 be added in this change or deferred to a follow-up?
- **Resolution**: Add the check in this change. Modify `run_log_flush.py` to reject terminal failure words (`stalled`, `bailed`) in pre-terminal snapshots, and add regression tests to `test_run_log_flush.py`.
- **Source**: user

## Decision 2: I-Slot-1 section placement
- **Question**: Should I-Slot-1 go under a new `## Panel integrity` section or the existing `## Agent contracts` section?
- **Resolution**: New `## Panel integrity` section. Panel slot accounting is a distinct concern from agent verdict contracts.
- **Source**: codebase (issue leaves this to designer)
