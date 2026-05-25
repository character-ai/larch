### Warnings

- **Step design Step 3 — aggregator OOS numbering — plan-review-loop.sh aggregator failed (exit 2)**:
  ```
Aggregator emitted 3 duplicate `### OOS_1:` headings in ballot.txt at offsets ~249/257/265.
Reviewers: Cursor-Edge, Cursor-Pragmatic, Cursor-dyn-schema-wire-consistency.
The aggregator preserved verbatim per-reviewer OOS blocks without global renumbering, even after a prose note claiming no OOS blocks existed.
Tally exited rc=2 ("duplicate or malformed FINDING/OOS headings in ballot").
Fix applied: orchestrator manually renumbered OOS_1/OOS_2/OOS_3 in ballot.txt, then re-ran tally-plan-review.sh directly with 3 voter files. TALLY_PLAN_REVIEW_STATUS=ok on re-run.
Follow-up issue should be filed against /design aggregator OOS numbering after this run completes.
  ```

- **Step design Step 5b — OOS filing graceful-degrade — file-design-oos.sh prepare failed (exit 0)**:
  ```
file-design-oos prepare returned FILE_DESIGN_OOS_DEPS_AVAILABLE=false (oos-file-conflict-deps.sh graceful-degrade with no caller TSV produced).
Single-item OOS batch (count=1) — intra-batch dep analysis would have no edges to detect anyway.
Proceeding with /larch:issue invocation WITHOUT --intra-batch-deps-file / --no-dep-llm (LLM dep-analysis runs against any existing open issues).
  ```
