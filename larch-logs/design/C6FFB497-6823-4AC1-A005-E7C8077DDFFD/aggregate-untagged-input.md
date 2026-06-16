### FINDING_1:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: security
- **Location**: skills/design/scripts/design-step3-mav.sh:83-94; skills/design/scripts/design-stage-terminal-state.sh:9-56; skills/design/scripts/design-failure-report.sh:9-43
- **Concern**: Quiet wrappers validate through the new child CLI only after larch_quiet_init. Scenario: For a rejected DESIGN_TMPDIR, these wrappers already have stderr redirected to a quiet log. The proposed child CLI message goes into that log instead of caller stderr, unlike the sourced bash validator which used larch_err. It can also create larch-quiet-*.log under a disallowed existing DESIGN_TMPDIR before rejection.
- **Proposed resolution**: Source lib-quiet if needed, but defer larch_quiet_init until after successful validate-design-tmpdir in these wrappers, or otherwise validate before quiet log selection.
