### FINDING_2: `postmerge_missing_manifest` harness diverges from real post-merge preconditions
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Concern**: The test omits `post-merge-sentinel` and related ordering/assertions used by sibling post-merge tests; the stubbed `larch-log` path can pass while production’s sentinel + bypass predicate chain regresses.
- **Suggested revision**: Add `touch post-merge-sentinel` (or equivalent), align assertions with other post-merge ordering tests, and assert the intended `status=done` / write-final-report / commit sequence where that is the regression signal you want.


