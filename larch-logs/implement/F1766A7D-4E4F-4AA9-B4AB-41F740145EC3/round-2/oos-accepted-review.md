### OOS_1: [OUT_OF_SCOPE] emit-layer golden tests are self-referential
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Emit-layer golden tests are self-referential (body rows are the expected stdout). They will not catch a body+emit pair that is internally consistent but wrong vs legacy wire order.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Keep integration subprocess tests; optionally add checked-in golden stdout fixtures from pre-refactor captures.


