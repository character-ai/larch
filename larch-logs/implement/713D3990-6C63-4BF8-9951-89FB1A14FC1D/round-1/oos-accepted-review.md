### OOS_1: [OUT_OF_SCOPE] `docs/run-logs.md` intro omits self-review tally write path
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-run-log-semantics-output.txt
- **Severity**: important
- **Concern**: The lead paragraph still attributes tally writing only to the Step 5 panel review loop (`review-and-fix CLI` / `review core`) and `review-findings-full.jsonl` round detail. Self-review skips that loop and writes via `write-self-review-tally` with an empty JSONL sentinel, so operators and doc readers can misread self-review runs as panel runs with missing artifacts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Update intro sentence to mention write-self-review-tally for self-review runs
  - From dyn-run-log-semantics-output.txt: Extend the **Written** line and the detail-storage paragraph to name both paths (panel loop vs `--self-review` / `write-self-review-tally`) and state which artifacts are intentionally absent for self-review.


