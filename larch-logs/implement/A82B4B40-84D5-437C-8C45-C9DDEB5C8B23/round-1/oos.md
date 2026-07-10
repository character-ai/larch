### FINDING_1: [OUT_OF_SCOPE] Step 2 mark failures are treated as success
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, dyn-dyn-token-attribution
- **Severity**: major
- **Concern**: Launcher-side Step 2 marking can return success even when no Step 2 row is actually persisted, so external runs miss the sidecar/execution-issues warning path and silently rely on other attribution fallbacks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-token-attribution: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

### FINDING_3: [OUT_OF_SCOPE] Raw-label fallback is missing in per-step role costing
- **Reviewer(s)**: codex-specialist-edge-cases, cursor-specialist-testing
- **Severity**: minor
- **Concern**: The per_step role-costing path still lacks raw-label fallback, so report-only reads can undercount or zero coder spend when they depend on a stale token report.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Mirror raw-label fallback in the per_step branch or rebuild reports from ledger before role costing.
  - From cursor-specialist-testing: Extend _implement_roles per_step path or document report-only limitation (pre-existing scope)


Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_4: Launcher Step 2 marking can duplicate on retry
- **Reviewer(s)**: codex-specialist-edge-cases, cursor-specialist-testing
- **Severity**: major
- **Concern**: Launcher-side Step 2 marking lacks a once-only guard or sentinel, so retried or resumed runs can emit duplicate Step 2 marks and split the same ledger twice.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Reuse the dispatcher sentinel or otherwise persist a launcher-local sentinel and skip duplicate marks on re-entry.
  - From cursor-specialist-testing: Skip mark when answers_file is set or step2 telemetry/ledger already marked; add launcher resume/retry regression tests


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

