### Warnings

- **Step plan-review voter-dispatch claude — agent launch-claude-review (voter parse-rate check) warning (exit 0)**:
  ```
slot=1
voter_tool=claude
judge_error_count=9
total_findings=9
total_ballot_items=9
voter_file=<TMPDIR>/claude-vote-output.txt
voter_sha256=9445fb4f2084c269336cd5b742a2d2c0a92872a77a9033a76b2c735bdf5ac934
--- first 200 bytes of voter output ---
The ballot file is blocked by an active background wait. Ending the turn to wait for the `<task-notification>`.
  ```

- **Step plan-review voter-dispatch claude — agent launch-claude-review (voter parse-rate check) warning (exit 0)**:
  ```
slot=1
voter_tool=claude
judge_error_count=5
total_findings=5
total_ballot_items=5
voter_file=<TMPDIR>/claude-vote-output.txt
voter_sha256=63c7dd12ed906a4188ad77e203a9d69127975823762b9694f8f18428138b9638
--- first 200 bytes of voter output ---
The system has an immediate-background wait active and is blocking reads on progress artifacts. I need to end this turn and wait for the `<task-notification>` before I can read the ballot.
  ```

design Step 5c session-transcript snapshot-skipped: Claude source snapshot materialization failed; transcript capture skipped.
