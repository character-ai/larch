### Warnings

- **Step plan-review voter-dispatch claude — agent launch-claude-review (voter parse-rate check) warning (exit 0)**:
  ```
slot=1
voter_tool=claude
judge_error_count=10
total_findings=10
total_ballot_items=10
voter_file=<TMPDIR>/claude-vote-output.txt
voter_sha256=49bdae61719302ef10a8335ab9351e1efb1fbc55da5e919eeef40cae12e63e6f
--- first 200 bytes of voter output ---
I need to wait for a background task to complete before I can read the ballot file.
  ```

- **Step plan-review voter-dispatch claude — agent launch-claude-review (voter parse-rate check) warning (exit 0)**:
  ```
slot=1
voter_tool=claude
judge_error_count=3
total_findings=3
total_ballot_items=3
voter_file=<TMPDIR>/claude-vote-output.txt
voter_sha256=d2233216acdc5bfc5a3b57fa2099f275921e73dab87b29cce0c230dec4b38846
--- first 200 bytes of voter output ---
There is an active background task — the harness is blocking file reads until it completes. I need to wait for the `<task-notification>` before the ballot file becomes readable. Please let me know w
  ```

design Step 5c session-transcript snapshot-skipped: Claude source snapshot materialization failed; transcript capture skipped.
