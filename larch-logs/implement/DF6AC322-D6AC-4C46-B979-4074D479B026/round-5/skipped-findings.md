### FINDING_3: Quoted finalize-state values can trigger false stall recovery
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-bash-parity-output.txt
- **Severity**: important
- **Concern**: Some Step 18 / stall-recovery reads still consume shell-quoted `finalize-state.sh` values literally, so values like `'false'` may be treated as truthy and spuriously enter stall recovery after restore/Python writes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From dyn-bash-parity-output.txt: Address the concern above.



