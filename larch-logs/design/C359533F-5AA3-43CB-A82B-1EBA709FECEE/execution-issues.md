### Warnings

- **Step plan-review voter-dispatch claude — agent launch-claude-review (voter parse-rate check) warning (exit 0)**:
  ```
slot=1
voter_tool=claude
judge_error_count=3
total_findings=3
total_ballot_items=3
voter_file=<TMPDIR>/claude-vote-output.txt
voter_sha256=bfd92a010be24fd793e0b53e0ee891bcfb3ed8044f18628bab4d87c438ba690d
--- first 200 bytes of voter output ---
There is an active background task blocking file reads. I need to wait for the `<task-notification>` before the ballot file becomes accessible. Please allow the background task to complete and then I
  ```

- **Step plan-review voter-dispatch claude — agent launch-claude-review (voter parse-rate check) warning (exit 0)**:
  ```
slot=1
voter_tool=claude
judge_error_count=2
total_findings=2
total_ballot_items=2
voter_file=<TMPDIR>/claude-vote-output.txt
voter_sha256=88f65ee0e108db81262a10aa6003b15590756319a4a59980aadc7979097d601e
--- first 200 bytes of voter output ---
I need to end this turn and wait for the background task to complete before I can read the ballot file.
  ```

design Step 5c session-transcript snapshot-skipped: Claude source snapshot materialization failed; transcript capture skipped.
