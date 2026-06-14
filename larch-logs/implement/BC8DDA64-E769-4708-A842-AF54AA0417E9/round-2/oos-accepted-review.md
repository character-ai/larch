### OOS_3: [OUT_OF_SCOPE] Out-of-manifest tracked/untracked pollution not fail-closed after coder dispatch
- **Reviewer(s)**: dyn-coder-dispatch-output.txt
- **Severity**: important
- **Concern**: The Python port drops shell fail-closed guards `round_tracked_dirty_outside_manifest`, `round_untracked_outside_manifest`, and `round_has_non_carryover_tracked_residue`. `_stage_and_commit_round` commits only manifest paths and returns success without checking whether the external coder left other tracked dirt or new untracked files outside `coder-stage-paths.txt`. A compromised or misbehaving Cursor/Codex run can leave extra changes in the working tree while the round reports `CODER_STATUS=applied`, weakening the trust boundary around accepted-finding dispatch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-coder-dispatch-output.txt: Port the three shell helpers and invoke them from `_stage_and_commit_round` (and any follow-up commit path) so tracked dirt or new untracked files outside the manifest fail the round with `CODER_STATUS=failed`, matching the prior `write_coder_failed_result` behavior; add pytest cases that simulate out-of-manifest tracked and untracked pollution after a mocked coder dispatch.


