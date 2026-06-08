### [Plan Review] FINDING_7

### FINDING_7: PyYAML dependency documentation remains tied to retired `lint-skill-invocations`
- **Reviewer(s)**: Cursor-dyn-consumer-sweep
- **Severity**: important
- **Concern**: The plan drops `lint-skill-invocations` hook dependencies as part of the stdlib Python port, but retained dependency-sync documentation still says PyYAML must stay in sync with `lint-skill-invocations` additional dependencies. The planned basename sweep may not catch these stale references.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-consumer-sweep: A named step: rewrite the header to document PyYAML only for remaining consumers (check-topology-rule-paths hook additional_dependencies and CI pre-commit env), not lint-skill-invocations
  - From Cursor-dyn-consumer-sweep: Add an explicit UPDATED bullet (or tighten the stale-reference sweep) to retarget the pin rule at check-topology-rule-paths (and requirements-lint.txt), drop the deleted .md pointer, and note lint-skill-invocations no longer uses PyYAML


### [Plan Review] FINDING_8

### FINDING_8: Stale-reference sweep misses retired `.md` sibling paths
- **Reviewer(s)**: Cursor-dyn-consumer-sweep, Codex-dyn-consumer-sweep
- **Severity**: important
- **Concern**: The plan’s stale-reference sweep focuses on retired script basenames or a generic `scripts/*.md` sweep, but retained docs still cite retired `.md` siblings such as mermaid, readability-preamble, and skill-invocations docs. After manifest updates and deletions, these stale references could fail retired-script linting or leave incorrect contracts behind.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-consumer-sweep: Include scripts/sanitize-mermaid-fragment.md and scripts/test-mermaid-fragments.md in the explicit stale-reference checklist (or repoint to python3 python/cli.py lint mermaid-fences)
  - From Codex-dyn-consumer-sweep: Expand the sweep to grep every manifest-added retired path, including .md siblings, and update these retained docs.


