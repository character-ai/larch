### FINDING_3: Test pins premature Bash mutation of `.step17-emitted`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `scripts/test-render-cost-line-callsites.sh` currently allows or pins the Bash-side `.step17-emitted` touch instead of enforcing that only orchestrator prose writes the sentinel after a successful verbatim emit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt: Address the concern above.



