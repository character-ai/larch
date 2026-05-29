### FINDING_20: age-only cleanup can delete long-idle live sessions
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Cleanup can delete session dirs idle longer than retention even if Claude is still running, breaking long-paused design or idle implement sessions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.



