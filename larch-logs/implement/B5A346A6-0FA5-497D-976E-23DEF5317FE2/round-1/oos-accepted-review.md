### OOS_1: [OUT_OF_SCOPE] `cleanup_implement_logs` `--run-dir` lacks `larch-logs/implement/` guard
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `python/cleanup_implement_logs.py:448-449` — `--run-dir` accepts any resolved path with no guard that it sits under `larch-logs/implement/`. A mistaken `--execute --run-dir <repo-root>` can run destructive `rglob` deletes across the tree. Identical footgun in the retired `scripts/cleanup-implement-logs.py`; not introduced or amplified by this move.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


