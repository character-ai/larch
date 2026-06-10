### OOS_1: [OUT_OF_SCOPE] Stale rubric references removed render-voter test target
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `skills/shared/review-acceptance-rubric.md` still names the removed `make test-render-voter-prompt` target. Maintainers following the rubric/fluff guidance can hit a missing Makefile target after the renderer harness migration.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Address the concern above.


