### [Plan Review] FINDING_2

### FINDING_2: `dispatch-code-voters.sh` cutover omits stale failure prose
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The plan repoints only the invocation and says "No other behavior change", but the non-zero path still logs `dispatch-with-waterfall.sh exited` at `scripts/dispatch-code-voters.sh:153`. Operators and log triage will see a deleted entrypoint name after cutover.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Extend the `### UPDATED: scripts/dispatch-code-voters.sh` step to reword the `larch_err` at line 153 to `agent dispatch-waterfall` (keep `set +e` / `set -e` semantics unchanged).


