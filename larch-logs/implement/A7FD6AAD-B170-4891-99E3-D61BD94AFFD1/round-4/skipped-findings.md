### FINDING_2: Unrelated #3175 hook expansion bundled into #3202 PR
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Large `hook-anti-read-poll.sh` / AGENTS / orchestrator-never changes unrelated to stderr-tail surfacing are bundled in the same PR as #3202. That couples features, makes bisect and review harder, and increases regression risk for unrelated behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Split hook/AGENTS/orchestrator-never changes to a separate PR or revert from this branch.



