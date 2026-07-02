### Warnings

- **Step design failure report — design-failure-report.sh failed (exit 0)**:
  ```
design failure report audit: operator-action:cancelled-outcome
  ```

- **Step plan-review voter-dispatch claude — agent launch-claude-review (voter parse-rate check) warning (exit 0)**:
  ```
slot=1
voter_tool=claude
judge_error_count=19
total_findings=19
total_ballot_items=19
voter_file=<TMPDIR>/claude-vote-output.txt
voter_sha256=88f65ee0e108db81262a10aa6003b15590756319a4a59980aadc7979097d601e
--- first 200 bytes of voter output ---
I need to end this turn and wait for the background task to complete before I can read the ballot file.
  ```

- **Step plan-review voter-dispatch claude — agent launch-claude-review (voter parse-rate check) warning (exit 0)**:
  ```
slot=1
voter_tool=claude
judge_error_count=8
total_findings=8
total_ballot_items=8
voter_file=<TMPDIR>/claude-vote-output.txt
voter_sha256=c056f07f8bb2fb78ea90e55575e73593263fb51add255e832948389f88c6ef44
--- first 200 bytes of voter output ---
There is an active background wait blocking file reads. I need to wait for the `<task-notification>` before I can read the ballot file and cast votes.
  ```

design Step 5c session-transcript snapshot-skipped: Claude source snapshot materialization failed; transcript capture skipped.
