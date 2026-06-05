### [Plan Review] FINDING_5

### FINDING_5: Python Step 8+ post-invoke handling can re-enter bash/state-file paths
- **Reviewer(s)**: Codex-Innovation, Cursor-dyn-json-state-contract
- **Severity**: important
- **Concern**: The shared post-invoke exit matrix remains bash-oriented after selecting the Python ship driver, including `ship-pr.sh` re-invocations and `ship-pr-state.sh` reads. Python runs can switch implementation paths mid-run or read the wrong state source for exit handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Make the re-invoke text selector-aware, e.g. re-run the same Step 8+ Invoke branch, and add a structure pin for the Python path
  - From Cursor-dyn-json-state-contract: Extend A1 to branch 1045-1067 explicitly (parse instruction, Exit 0/3/4/6 bullets, OOS checkpoint fork-flag reads) for python vs bash; add A2 greps for python re-invoke targets on Exit 0 and Exit 6, not only exit-code mapping pins


