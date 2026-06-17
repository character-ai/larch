### Warnings

- **Step design Step 5b — larch:issue (degraded intra-batch deps) failed (exit 0)**:
  ```
design Step 5b OOS filing used the graceful-degrade path: FILE_DESIGN_OOS_DEPS_AVAILABLE=false (intra-batch deps TSV unavailable/empty). The single rolled-up OOS item has no intra-batch dependency edges, so /larch:issue was invoked without --intra-batch-deps-file / --no-dep-llm. Filing succeeded: issue #4598 created, blocked by #4595. Benign for a single-item batch.
  ```
