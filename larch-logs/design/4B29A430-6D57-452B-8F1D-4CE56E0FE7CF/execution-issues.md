### Warnings

- **Step plan-review voter-dispatch claude — agent launch-claude-review (voter parse-rate check) warning (exit 0)**:
  ```
slot=1
voter_tool=claude
judge_error_count=7
total_findings=7
total_ballot_items=7
voter_file=<TMPDIR>/claude-vote-output.txt
voter_sha256=a9b261cc625f8e9c113c7b1ee881e69c50c856c088038f3f64c2dfdad9a1fbcc
--- first 200 bytes of voter output ---
I need to wait for the background task to complete before I can read the ballot file.
  ```

- **Step plan-review voter-dispatch claude — agent launch-claude-review (voter parse-rate check) warning (exit 0)**:
  ```
slot=1
voter_tool=claude
judge_error_count=6
total_findings=6
total_ballot_items=6
voter_file=<TMPDIR>/claude-vote-output.txt
voter_sha256=943a467b6cdad07034b05c04177d13b00e1d142bc835ab795f8efc955d5f42d2
--- first 200 bytes of voter output ---
A larch background-wait hook is blocking all tool calls. I must end this turn without polling and wait for the `<task-notification>`.
  ```

design Step 5c session-transcript snapshot-skipped: Claude source snapshot materialization failed; transcript capture skipped.
