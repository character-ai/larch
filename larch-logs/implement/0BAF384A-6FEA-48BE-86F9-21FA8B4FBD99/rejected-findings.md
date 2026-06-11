### [rejected] FINDING_3

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_3: Upgrade success omits restart-required key
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: A verified version upgrade emits `LARCH_NEW_VERSION_INSTALLED=true` but not `LARCH_RESTART_REQUIRED=true`, even though callers need the restart key after an install that requires restart.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** dismissed (0 YES)

### FINDING_4: Deleted issue-list edge coverage was not ported
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Deleted shell harness coverage for multi-page pagination, `closed-window-days=0`, and `#1063` title-prefix edge cases was not ported to pytest. Regressions in `_json_documents` or `_title_archival` may pass CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

