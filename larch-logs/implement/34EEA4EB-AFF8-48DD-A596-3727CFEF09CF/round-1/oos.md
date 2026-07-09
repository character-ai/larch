### FINDING_4: [OUT_OF_SCOPE] Progress-report retirement residue and doc sweep
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-testing, cursor-specialist-plan-fidelity-auto
- **Severity**: minor
- **Concern**: The retired live-discovery / mid-run report surface, its legacy tests, and the planned doc sweep still remain, but that cleanup was explicitly deferred.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Finish the planned deletion after consumer audit.
  - From cursor-specialist-correctness: Complete the planned doc sweep.
  - From cursor-specialist-testing: Prune when mid-run code is deleted.
  - From cursor-specialist-testing: Update doc to describe statusline plus render-phase-detail.
  - From cursor-specialist-plan-fidelity-auto: Add the three planned doc updates or explicitly defer them in the plan


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_15: [OUT_OF_SCOPE] Statusline-install policy residue
- **Reviewer(s)**: cursor-specialist-correctness, dyn-dyn-statusline-security
- **Severity**: minor
- **Concern**: The local statusLine merge policy, bash -lc chaining choice, one-time notice handling, and bootstrap stderr leakage are policy/diagnostic concerns rather than an active exploit path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Document the manual opt-in path or offer a documented merge strategy.
  - From dyn-dyn-statusline-security: No change unless chaining policy changes.
  - From dyn-dyn-statusline-security: Address the concern above.
  - From dyn-dyn-statusline-security: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_16: [OUT_OF_SCOPE] Miscellaneous architecture residuals
- **Reviewer(s)**: cursor-specialist-edge-cases, dyn-dyn-statusline-security
- **Severity**: minor
- **Concern**: The retained env pointer writer, registry-scan latency note, and round_runner breadcrumb wiring are residual architecture/optimization items outside the current review scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Defer unless consumer audit completes.
  - From cursor-specialist-edge-cases: Optimize only if profiling shows >50ms refreshes.
  - From dyn-dyn-statusline-security: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_17: [OUT_OF_SCOPE] Atomic append note
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: Plain open("a") append may interleave under heavy concurrent writes, but that is only a theoretical retention note here.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Consider O_APPEND or atomic line write if interleaving becomes observed.
Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

