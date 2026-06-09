### OOS_4: [OUT_OF_SCOPE] Audit-run docs still describe file-glob behavior
- **Reviewer(s)**: dyn-signal-migration-correctness-output.txt
- **Severity**: nit
- **Concern**: Operator-facing audit docs still describe old file-glob/meta sidecar behavior for scans that migrated to `reviewer_signals`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-signal-migration-correctness-output.txt: Address the concern above.


### OOS_5: [OUT_OF_SCOPE] accepted-low-value summary prints misleading 0/0 percentage
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: The accepted-low-value line does not guard zero accepted findings and can print misleading `0.0% (0/0)`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


