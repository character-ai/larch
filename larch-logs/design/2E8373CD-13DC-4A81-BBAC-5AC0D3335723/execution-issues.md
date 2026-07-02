### Warnings

- **Step plan-review voter-dispatch claude — agent launch-claude-review (voter parse-rate check) warning (exit 0)**:
  ```
slot=1
voter_tool=claude
judge_error_count=21
total_findings=21
total_ballot_items=21
voter_file=<TMPDIR>/claude-vote-output.txt
voter_sha256=654bb165add3ed073ed756780f1e311948fd97204f21346abde6e39eb23e390f
--- first 200 bytes of voter output ---
There is an active background task blocking file reads. I need to wait for it to complete before I can read the ballot. Please wait for the background task notification, then I can proceed with the vo
  ```

- **Step plan-review voter-dispatch claude — agent launch-claude-review (voter parse-rate check) warning (exit 0)**:
  ```
slot=1
voter_tool=claude
judge_error_count=13
total_findings=13
total_ballot_items=13
voter_file=<TMPDIR>/claude-vote-output.txt
voter_sha256=04ae74cd99f05a37b23cfee81fbb9d93fbc5af5c05a81bbd8abfc594b24938f6
--- first 200 bytes of voter output ---
A background task is currently blocking reads. Ending the turn to wait for the task notification before casting votes.
  ```

design Step 5c session-transcript snapshot-skipped: Claude source snapshot materialization failed; transcript capture skipped.
