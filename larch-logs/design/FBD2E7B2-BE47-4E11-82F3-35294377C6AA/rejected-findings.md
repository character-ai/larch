### [Plan Review] FINDING_5

### FINDING_5: Step 5 MAV/coder durable-bail routing must survive the stall remap
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: major
- **Concern**: Rewriting pre-ship exhaustion as `NEXT_ACTION=stall` can accidentally route `step5-mav` or `coder-main-agent-required` terminal stalls through generic Step 18 handling, dropping the existing `--record-only` plus Durable Bail path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: A explicit preserve directive: keep the Step 5 MAV/coder `NEXT_ACTION=stall` durable-bail paragraph unchanged when editing section 4; add a structure-test needle requiring it
  - From Cursor-Pragmatic: In the new site-routing table, list step5-mav and coder paths separately: stall remains the repair-loop action, but orchestrator handling stays the existing durable-bail paragraph; add a structure-harness assertion that this override survives the exhausted-to-stall remap


### [Plan Review] FINDING_6

### FINDING_6: Recoverable no-delta attempts must restore their pre-dispatch state
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Concern**: Continuing to the next tier after timeout, launcher failure, or no useful change without restoring the captured attempt baseline can leave partial edits, index changes, `HEAD` changes, or untracked files behind. Those remnants can pollute later tiers and produce false useful-delta detection or incorrect exhaustion outcomes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: After classifying a recoverable tier as no useful delta, restore the captured pre-dispatch snapshot (tracked, index, untracked, HEAD) before calling next_untried_tier(); keep fail-closed behavior for structural/forbidden/integrity failures without silent acceptance


### [Plan Review] FINDING_8

### FINDING_8:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/implement/checks_lint_fix.py:685-703
- **Concern**: [SCOPE-REDUCTION] Per-tier content baselines should reuse existing digest capture instead of new parallel machinery. Scenario: The plan requires content-aware dirty-path detection, but `_delta_paths_after_dispatch()` compares path membership only; adding a second bespoke digest scheme duplicates `dispatch_helpers._write_prelaunch_digests()` already used for pre-dispatch content snapshots
- **Proposed resolution**: Reuse or factor the existing SHA-256 digest helper for per-tier pre/post snapshots on already-dirty tracked and untracked paths; treat content hash change as useful delta


