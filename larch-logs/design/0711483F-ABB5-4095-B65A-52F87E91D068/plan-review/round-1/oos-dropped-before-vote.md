### OOS_2: Invariant persist verb still emits no machine persist rows
- **Description**: Invariant persist verb still emits no machine persist rows. Scenario: Guideline persist emits ARCHITECTURAL_GUIDELINE_ASSESSMENT_PERSIST_* stdout on every attempt; invariant persist does not. Post-fix audits still cannot distinguish invariant helper-not-called from helper-failed from CLI output alone.
- **Reviewer**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: python/larch/core/architectural_guidelines.py:2063-2107
- **Phase**: design

