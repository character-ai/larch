### OOS_4: [OUT_OF_SCOPE] normalize-issue-env path-containment harness gap
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: Case 21 path-containment tests cover other stall-recovery outputs but not `normalize-issue-env --issue-stdout-file` / `--output-file`; runtime guards exist, so this is a harness-only gap.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


### OOS_5: [OUT_OF_SCOPE] test-stall-recovery-report.md omits normalize-issue-env case docs
- **Reviewer(s)**: dyn-prompt-protocol-output.txt
- **Severity**: nit
- **Concern**: The sibling `.md` contract text does not enumerate the `normalize-issue-env` harness cases, a doc-sync gap rather than a runtime defect.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-prompt-protocol-output.txt: Address the concern above.

