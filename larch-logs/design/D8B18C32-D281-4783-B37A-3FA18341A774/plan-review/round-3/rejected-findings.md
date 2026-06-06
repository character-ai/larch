### [Plan Review] FINDING_1

### FINDING_1: safe_step_value rewrite bundled into wiring-only bugfix
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: `safe_step_value` full-string rewrite is bundled into a wiring-only bugfix. For #3568 (silent `ITEMS_TOTAL=0` from heading-less bug-body), `issue-input-file` already exists and the prefix glob already maps `8a<script>` to `unknown`; roughly half the planned diff is sanitizer churn unrelated to filing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Drop the safe_step_value rewrite from this PR; wire issue-input-file in stall-recovery.md plus the structure/parse-input pins only


