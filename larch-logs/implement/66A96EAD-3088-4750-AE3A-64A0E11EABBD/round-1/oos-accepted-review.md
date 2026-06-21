### OOS_1: [OUT_OF_SCOPE] Missing `test_agents` coverage for absent drafter scout block
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Plan-listed test for missing drafter scout block recording `SCOUT_FAIL_REASON=absent` is not present. Drafter absent-scout behavior can regress without CI signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add parse_drafter_output test asserting scout_fail_reason=absent when LARCH_SCOUT markers are omitted.


