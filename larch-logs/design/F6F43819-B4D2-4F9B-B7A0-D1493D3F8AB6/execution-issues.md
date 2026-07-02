### Warnings

- **Step plan-review voter-dispatch claude — agent launch-claude-review (voter parse-rate check) warning (exit 0)**:
  ```
slot=1
voter_tool=claude
judge_error_count=15
total_findings=15
total_ballot_items=15
voter_file=<TMPDIR>/claude-vote-output.txt
voter_sha256=6820aa8d12506a56671aa433faad39976f075e18f80da0ff34304d69dda57532
--- first 200 bytes of voter output ---
I'm unable to read the ballot file. The Read tool is returning this error on every attempt:

> An immediate-background wait is active. End the turn and wait for `<task-notification>`; do not poll prog
  ```

- **Step plan-review voter-dispatch claude — agent launch-claude-review (voter parse-rate check) warning (exit 0)**:
  ```
slot=1
voter_tool=claude
judge_error_count=15
total_findings=15
total_ballot_items=15
voter_file=<TMPDIR>/claude-vote-output.txt
voter_sha256=a9b261cc625f8e9c113c7b1ee881e69c50c856c088038f3f64c2dfdad9a1fbcc
--- first 200 bytes of voter output ---
I need to wait for the background task to complete before I can read the ballot file.
  ```

design Step 5c session-transcript snapshot-skipped: Claude source snapshot materialization failed; transcript capture skipped.
