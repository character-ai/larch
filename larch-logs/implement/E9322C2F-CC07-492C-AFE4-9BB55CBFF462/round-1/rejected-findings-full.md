### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: Duplicated dispatch stub heredoc can drift
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `skills/design/scripts/test-plan-review-loop.sh:73-96` duplicates `write_dispatch` logic in `write_dispatch_combined_threshold` for one KV, increasing future maintenance drift risk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Parameterize write_dispatch with COMBINED_FALLBACK_COUNT default 0 and reuse from threshold scenario.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: Consumers trust missing or inconsistent COMBINED_FALLBACK_COUNT
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Consumers in `skills/design/scripts/dispatch-plan-review-panel.sh`, `skills/design/scripts/plan-review-loop.sh`, and `skills/design/scripts/decompose-panel-dispatch.sh` trust `COMBINED_FALLBACK_COUNT` or default it to `FALLBACK_COUNT` when absent. If `PHASE2_RELAUNCH_COUNT` survives but `COMBINED_FALLBACK_COUNT` is missing or understated, degradation decisions may ignore phase-2-only overload.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Recompute or clamp COMBINED when PHASE2 is present; or fail closed on inconsistent/missing COMBINED.
  - From cursor-specialist-edge-cases-output.txt: Extend guard to recompute from PHASE2 when COMBINED missing; add harness omitting only COMBINED.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: CP_STUB_FAIL_COUNT=0 silently disables intended failures
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: In `scripts/test-dispatch-with-waterfall.sh:82-94`, `CP_STUB_FAIL_COUNT=0` disables all stub failures silently. A misconfigured multi-fall-through scenario with `CP_STUB_FAIL_TARGET_CONTAINS` set could pass without exercising reuse-copy failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Treat 0 as unset/default 1 or error when fail target is configured.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

