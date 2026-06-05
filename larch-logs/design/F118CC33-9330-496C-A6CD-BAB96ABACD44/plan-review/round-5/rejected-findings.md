### [Plan Review] FINDING_2

### FINDING_2: Extra implement timing env pins may duplicate the design-only fallback gate
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The plan adds `LARCH_TIMING_SKILL=implement` and related harness expectations across multiple implement callers even though `timing-report.sh` can already gate `resolve_workflow_fallback` to design. This may unnecessarily expand production and test surface without demonstrating a post-gate leak.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Keep the timing-report.sh design-only gate and markdown/json omission work; drop the extra caller env-pin and harness surface unless a post-gate leak is demonstrated; narrow acceptance grep so it does not require LARCH_TIMING_SKILL=implement at every production caller


