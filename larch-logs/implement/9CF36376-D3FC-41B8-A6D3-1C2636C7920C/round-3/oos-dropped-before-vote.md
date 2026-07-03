### OOS_1: [OUT_OF_SCOPE] Cancellation/final-summary paths still bypass the log-publish choke point
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: Cancellation and final-summary terminal paths can still commit logs without the new pre-copy enrichment because they do not flow through the centralized `design log-publish` path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: File a follow-up if cancellation committed logs need the same choke-point behavior.

### OOS_2: [OUT_OF_SCOPE] Hermetic `gh` stub is missing from PATH in the enriched integration test
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: nit
- **Concern**: The enriched `design log-publish` integration test can fail or pick up host tooling because it does not prepend the stub `bin_dir` to `PATH`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Prepend bin_dir to PATH the same way _run_publish does.

### OOS_3: [OUT_OF_SCOPE] Clarify follow-up final-summary handling still re-renders and can leave stale status
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: important
- **Concern**: Clarify's follow-up final-summary path still re-renders instead of reusing the summary already written by `design log-publish`, and a failed tracking-comment upsert can leave `CLARIFY_PUBLISH_STATUS=ok` / `PUBLISH_OK=true` with a stale `larch:final-summary` comment.

