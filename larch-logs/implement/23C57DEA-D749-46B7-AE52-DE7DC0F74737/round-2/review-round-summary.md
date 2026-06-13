# Review Round 2

- Mode: `diff`
- 2 accepted, 2 rejected (1 neutral)

## Accepted Findings

### FINDING_3: Awk/sort TSV extraction failures misreported as no overlapping tasks
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-best-effort-shell-output.txt
- **Severity**: important
- **Concern**: In `scripts/render-review-phase-detail.sh`, awk/sort/head extraction failures are handled like a successful empty overlap set. Under `set -o pipefail`, pipeline failure can clear `sorted_file` / `tasks_file` and the script prints `No reviewer timing tasks overlapped this round.` even when overlapping `type=vendor` rows exist in `timing-ledger.tsv`. That violates the documented contract reserving the no-task note for truly empty successful extraction; operators may believe the round had no reviewer activity when extraction actually failed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Track whether extraction produced rows (e.g. pre-sort line count or a guarded awk pass). On pipeline failure with a valid round window, emit Reviewer timing chart unavailable. Reserve the no-task note for a successful empty extraction. Add a harness regression.
  - From dyn-best-effort-shell-output.txt: Record extraction failure explicitly (for example `if ! awk … | LC_ALL=C sort … >"$sorted_file"; then extraction_failed=1; : >"$sorted_file"; fi`, and the same pattern for `head`), then branch on three outcomes: non-empty `tasks_file` → guarded renderer call; `extraction_failed=1` or renderer non-zero → `Reviewer timing chart unavailable.`; only otherwise → the no-task note.


### FINDING_4: No test for gantt CLI empty-filtered stdout contract (exit 0, empty stdout)
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The plan requires gantt render to exit 0 with empty stdout when all TSV rows are filtered out; no test covers that CLI contract. If `gantt_render_main` later returns non-zero on empty filtered output, `render-review-phase-detail.sh` may mislabel overlapping vendor data as chart unavailable instead of no overlap.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add pytest: TSV rows outside window flags, assert subprocess returncode 0 and stdout empty.


