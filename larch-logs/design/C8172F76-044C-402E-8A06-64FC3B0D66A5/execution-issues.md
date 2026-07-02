### Warnings

- **Step plan-review voter-dispatch claude — agent launch-claude-review (voter parse-rate check) warning (exit 0)**:
  ```
slot=1
voter_tool=claude
judge_error_count=13
total_findings=13
total_ballot_items=13
voter_file=<TMPDIR>/claude-vote-output.txt
voter_sha256=60f41e82117f8581ae52bf7edecdad6db45ee6f8468a79bdb5019e12aaf6013b
--- first 200 bytes of voter output ---
I need to wait for the background task to complete before the ballot file is accessible.
  ```

- **Step plan-review voter-dispatch claude — agent launch-claude-review (voter parse-rate check) warning (exit 0)**:
  ```
slot=1
voter_tool=claude
judge_error_count=2
total_findings=2
total_ballot_items=2
voter_file=<TMPDIR>/claude-vote-output.txt
voter_sha256=4af4c61f3d3e316c1a4f44b033228831b10538154eed691eca69ef2722e13424
--- first 200 bytes of voter output ---
I need to wait for the background task to complete before I can read the ballot. Ending turn to await the `<task-notification>`.
  ```

design Step 5c session-transcript snapshot-skipped: Claude source snapshot materialization failed; transcript capture skipped.
