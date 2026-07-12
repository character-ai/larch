### FINDING_6: Accepted Step 5c partitioning must terminate after final summary
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Concern**: If Step 5c accepts partitioning after a publish-time oversize result, the flow may continue ordinary publishing after filing, annotating, migrating dependencies, and closing the original issue. This conflicts with the approved-partition terminal behavior and risks targeting a closed or obsolete issue.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: State explicitly that Step 5c Split-path acceptance exports SUMMARY_OUTCOME=approved-partition, runs the Final summary block, and exits 0 like Step 2b.5; only Override reruns design-step5c.sh.


### FINDING_7: Gate migrate-deps with session-backed live-mutation authorization
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Concern**: The new `migrate-deps` path may mutate production dependency graphs directly without validating `LARCH_LIVE_MUTATION_OK`, unlike the session-gated issue-filing path. A replayed or harness temporary directory could therefore authorize unintended mutations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Require migrate-deps_main to validate source-env.sh with check_live_mutation_auth before any dependency read or block-issue mutation, refuse with stable DECOMPOSE_DEPS_STATUS rows on denial, and add a test proving zero gh calls when unauthorized.


### FINDING_8: Ensure unrecoverable validation failure still presents exactly one question
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Concern**: If inline repair cannot produce a valid multi-piece acyclic proposal, the flow may terminate before presenting the required single partition question. That violates the requirement that every partition process offer partition, override, other, or chat choices through exactly one question.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Define a terminal fallback that still emits exactly one AskUserQuestion when proposal validation cannot be repaired, or explicitly route the failure through one existing partition question before terminating; add a test for unrecoverable proposal validation failure


