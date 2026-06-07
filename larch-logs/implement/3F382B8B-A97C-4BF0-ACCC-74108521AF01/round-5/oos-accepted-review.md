### OOS_20: [OUT_OF_SCOPE] Missing tmpdir validation in retally merge writer
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `persist-retally-step3-env.sh` accepts any existing `--design-tmpdir` and performs merge writes without the newer `larch_design_tmpdir_validate` hardening used by `plan-review-continuation.sh`; exploitability is low in normal orchestration but defense-in-depth is weaker.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Add `larch_design_tmpdir_validate` (and canonicalize with `pwd -P`) before merge writes, matching `plan-review-continuation.sh`.


### OOS_21: [OUT_OF_SCOPE] `write-after` caller appears absent outside tests
- **Reviewer(s)**: dyn-orchestrator-output.txt
- **Severity**: latent
- **Concern**: `snapshot-plan-round.sh write-after` is documented as part of the Gate B / `design-postplan-emit.sh` surface, but no shipped shell caller appears to invoke it outside tests; source marked this as predating the branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-orchestrator-output.txt: Address the concern above.


### OOS_22: [OUT_OF_SCOPE] Cumulative artifact retains Gate B skipped findings until render
- **Reviewer(s)**: dyn-artifact-state-output.txt
- **Severity**: nit
- **Concern**: `accepted-plan-findings-all.md` is appended before Gate B and retains skipped findings until `render-final-summary.sh` filters them, a pre-existing contract choice made more visible by multi-round accumulation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-artifact-state-output.txt: Address the concern above.


### OOS_23: [OUT_OF_SCOPE] Continuation heuristic asymmetry predates artifact work
- **Reviewer(s)**: dyn-artifact-state-output.txt
- **Severity**: important
- **Concern**: The design continuation helper’s one-Important and degraded-panel continuation thresholds diverge from the cited `/implement` thresholds; source marked this as outside its artifact/env consistency scope and not a regression in that area.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-artifact-state-output.txt: Address the concern above.

