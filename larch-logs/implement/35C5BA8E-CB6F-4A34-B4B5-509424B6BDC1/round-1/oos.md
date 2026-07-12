### FINDING_4: Final crashed tiers are not recorded in lineage [OUT_OF_SCOPE]
- **Reviewer(s)**: cursor-specialist-correctness, dyn-dyn-crash-provenance
- **Severity**: major
- **Concern**: Exhausted or unavailable crash paths omit the crashed tier from lineage, allowing a later `--start` to retry an already-consumed tier.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From dyn-dyn-crash-provenance: On every clean-`HEAD` crash at the launch commit where the tier actually ran, append one lineage row before returning (use `operator-bail` for terminal exhaustion/unavailability, `retry-next-tool` when advancing). Extend `_persist_crash_lineage` to accept the result token. Add a test that after final-tier crash, `--start` tier selection sees all three tiers attempted and routes to `ci-fix-exhausted`.


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_6: Salvage provenance is spoofable [OUT_OF_SCOPE]
- **Reviewer(s)**: codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases
- **Severity**: major
- **Concern**: Salvage reship is authorized by a predictable commit subject rather than lane-bound provenance, so an unrelated commit can be mistaken for fixer salvage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Write and validate identity-bound salvage provenance such as a trailer or sidecar.
  - From cursor-specialist-edge-cases: If tightening is desired later, bind salvage to lane-owned pathspec or commit metadata beyond subject matching.
  - From codex-specialist-edge-cases: Write and verify deterministic lane-identity provenance on the salvage commit or in a durable sidecar before reshipping.


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=true

### FINDING_10: Step 8 summary omits crash branching [OUT_OF_SCOPE]
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: The skill summary does not mirror the documented non-zero `BGJOB_RC` crash-finalization branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

### FINDING_13: Finalize shell harness is not in default CI [OUT_OF_SCOPE]
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: Shell regressions in `test-step-8-ci-fixer.sh` are not exercised by the default test-harness shards.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_14: Wrapper harness is not exercised by dispatch tests [OUT_OF_SCOPE]
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: Dispatch tests do not execute the Step 8 wrapper, leaving harness-only regressions dependent on manual runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_15: Salvage attribution edge cases lack tests [OUT_OF_SCOPE]
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: Wrong-parent and multi-commit salvage-shaped histories are not tested against narrow salvage validation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_20: Crash tier availability can disagree with degraded-tool state [OUT_OF_SCOPE]
- **Reviewer(s)**: dyn-dyn-crash-provenance
- **Severity**: minor
- **Concern**: Crash tier selection relies on `shutil.which` and may report exhaustion even when session environment state says a tier is configured.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-crash-provenance: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_21: Malformed zero-valued BGJOB_RC is not fail-closed [OUT_OF_SCOPE]
- **Reviewer(s)**: dyn-dyn-crash-provenance
- **Severity**: minor
- **Concern**: Bash numeric comparison can treat malformed `BGJOB_RC=00` as success and route to merge/status handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-crash-provenance: Address the concern above.
Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false
