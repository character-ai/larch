### FINDING_3: marker-delete-failed can leave restored state and continue as a fresh run
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `design-pause-load.sh` copies the restored snapshot into `DESIGN_TMPDIR` before marker deletion; if marker deletion fails, Step 0b treats `LOAD_OK=false` as fresh-run continuation, leaving restored artifacts in place and allowing new run state to mix with stale restored state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.



