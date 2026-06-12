### OOS_3: [OUT_OF_SCOPE] Stale debate-retry migration prose remains
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `docs/python-migration.md` still contains stale render debate-retry parity prose. The issue is docs-only, but it can mislead readers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### OOS_4: [OUT_OF_SCOPE] eval-5 still targets deleted dialectic protocol
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `eval-5` still targets deleted `dialectic-protocol.md`. Manual `eval-research` runs may expect removed files.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### OOS_5: [OUT_OF_SCOPE] Step 3 review fixtures still use stale schema fields
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `test-run-step3-review` fixtures still write `design_classification` and `workflow_path`. Classification cleanup grep can fail, and stale schema may hide regressions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


