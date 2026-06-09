### OOS_26: [OUT_OF_SCOPE] Retired read-session-env-key references remain in docs
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: SECURITY.md and the degraded-tools gate contract still document the deleted `read-session-env-key.sh` path instead of the Python `session read-key` boundary, risking script-not-found failures or reintroduction of bash read paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


### OOS_27: [OUT_OF_SCOPE] design structure pins still grep retired helper basename
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-design-structure.sh` still structurally pins `write-design-current-env.sh`, so CLI-only prose cleanup could fail structure tests despite correct runtime behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### OOS_28: [OUT_OF_SCOPE] Step 2a prose names retired read-design-classification helper
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `skills/design/SKILL.md` Step 2a prose still names `read-design-classification.sh` while the command fence uses `session read-classification`, inviting manual invocation of a retired script.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### OOS_29: [OUT_OF_SCOPE] setup larch-log carryover copies unsafe prior trees or symlinks
- **Reviewer(s)**: cursor-specialist-security-output.txt, codex-specialist-security-output.txt
- **Severity**: important
- **Concern**: `setup` copies `PREV_IMPLEMENT_TMPDIR/larch-logs` without sufficient trust-boundary checks; prior log trees or symlinked log files can be copied into the new session, potentially dereferencing readable secrets and hiding the symlink before later publication checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From codex-specialist-security-output.txt: Address the concern above.


