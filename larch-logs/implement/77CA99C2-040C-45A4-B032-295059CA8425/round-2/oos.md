### FINDING_5: Unify attempt allocation across lane and finalize
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: major
- **Concern**: Attempt allocation is split between `fixer-rounds.tsv` in the lane and lineage TSV append during finalize. A successful bgjob followed by failed finalize can leave the attempt recorded, causing a retry with the same `ATTEMPT` to wedge on “attempt was already recorded.” Unify attempt allocation or support finalize-only retry when the launch envelope already has a completed bgjob.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_9: [OUT_OF_SCOPE] Expand wrapper harness lifecycle coverage
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: The wrapper harness remains smoke-level and lacks lifecycle fixture coverage. Multi-tier retry and scope-routing regressions may therefore slip past CI. Expand the plan-listed Python integration tests rather than relying only on shell string checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_10: [OUT_OF_SCOPE] Enforce canonical temporary-directory containment
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: `safe_root` does not enforce canonical containment beneath a sessions root, leaving residual TOCTOU risk if `IMPLEMENT_TMPDIR` is attacker-controlled before start. Align with Python `_canonical_dir` containment checks if the threat model requires it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_11: [OUT_OF_SCOPE] Add thin launcher fences for Step 8
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: Step 8 lacks thin launcher fences for start, wait, and finalize, leaving room for the orchestrator to improvise polling or skip finalize. Add pinned Bash fences consistent with the other implement steps.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_14: [OUT_OF_SCOPE] Register the wrapper harness in CI shards
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: The wrapper smoke harness is not included in Makefile CI shards, so default-branch CI may never execute it. Register the harness in a test-harnesses shard if operators want CI enforcement.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_15: [OUT_OF_SCOPE] Reject duplicate sidecar keys consistently
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: Lane sidecar parsing uses first-wins duplicate handling unlike strict materializer writes. Tampered duplicate sidecar rows may pass when the first value matches expected identity. Switch lane sidecar parsing to strict exact-key validation matching the materializer.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_16: [OUT_OF_SCOPE] Clarify waterfall retry semantics in documentation
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: The documentation describes a one-tier waterfall while listing three delegated tiers, which may cause operators to misread retry semantics. Rephrase to describe per-attempt single-tier bgjob execution with multi-tier waterfall progression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.
Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false
