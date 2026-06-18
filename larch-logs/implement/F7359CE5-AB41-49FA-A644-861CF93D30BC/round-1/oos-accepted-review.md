### OOS_1: [OUT_OF_SCOPE] risk-integration: `docs/linting.md:222` — `test-classify-bump` shard label mismatch
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-harness-drift-output.txt
- **Severity**: important
- **Concern**: The `make test-classify-bump` row still says `test-harnesses-20`, but `Makefile:140` assigns `test-classify-bump` to `test-harnesses-19`. This branch edits the linting row without fixing the shard label, so operators debugging a classify-bump failure can inspect the wrong CI matrix job.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-drift-output.txt: Change the row to `test-harnesses-19`, or move the target in the Makefile if shard 20 was intended; keep `docs/linting.md` and the Makefile shard list aligned.


