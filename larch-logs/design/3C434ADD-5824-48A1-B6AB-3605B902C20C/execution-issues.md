### Warnings

- **Step plan-review voter-dispatch claude — agent launch-claude-review (voter parse-rate check) warning (exit 0)**:
  ```
slot=1
voter_tool=claude
judge_error_count=14
total_findings=14
total_ballot_items=14
voter_file=<TMPDIR>/claude-vote-output.txt
voter_sha256=d901c52815d33ce0d92934bccac2da3276239bdc12fcf04ab9ee710847e7e697
--- first 200 bytes of voter output ---
I'm unable to read the ballot file at this time. The tool system is blocking all file reads with:

> An immediate-background wait is active. End the turn and wait for `<task-notification>`; do not pol
  ```

- **Step plan-review voter-dispatch claude — agent launch-claude-review (voter parse-rate check) warning (exit 0)**:
  ```
slot=1
voter_tool=claude
judge_error_count=9
total_findings=9
total_ballot_items=9
voter_file=<TMPDIR>/claude-vote-output.txt
voter_sha256=775f138d6122340a3fd91515f55625a55a489039ed5c91ddc2c96a162028000d
--- first 200 bytes of voter output ---
I cannot read the ballot file — the harness is blocking all reads due to an active immediate-background wait. Ending the turn to wait for the `<task-notification>` before proceeding.
  ```

design Step 5c session-transcript snapshot-skipped: Claude source snapshot materialization failed; transcript capture skipped.
