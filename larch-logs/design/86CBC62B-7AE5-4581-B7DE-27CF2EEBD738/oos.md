### FINDING_3: Security-sidecar checkpoint mapping still needs a code-path update
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: `_after_checkpoint` still maps every non-zero checkpoint return code to `status=disposition_checkpoint_failed`. Without a dedicated `rc=3` branch, `cmd_file` cannot emit `status=security_sidecar_present` after the checkpoint change, and `dispatch_ship.py` will keep routing mixed runs to `halt-oos`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: The plan item 7 intent is right; make the `_after_checkpoint` rc=3 mapping an explicit approach sub-step (distinct stderr message, `step9a1_stamped=False`, run statistics when URLs exist) so it is not lost during implementation.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

