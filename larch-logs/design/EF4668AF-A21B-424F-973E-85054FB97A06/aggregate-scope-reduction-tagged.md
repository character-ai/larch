### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/agent_waterfall.py:412-567
- **Concern**: [SCOPE-REDUCTION] Half-mark anchor calls a full `cli.py agent collect-results` subprocess per finished slot inside the reap poll loop. Scenario: The reap loop cannot poll other launches or enforce the straggler deadline while a subprocess runs; with many slots this serializes anchor work and can push the real cutoff well past `clamp(2.5 × anchor, 300s, --timeout)`, partly defeating the feature
- **Proposed resolution**: Implement `_slot_collector_accepted` via an in-process helper imported from `collect_results` (shared with `_apply_collector_block`) that reads the existing `.done` sentinel and returns the same OK/cap_hit + gate predicate without spawning a new Python process per slot
