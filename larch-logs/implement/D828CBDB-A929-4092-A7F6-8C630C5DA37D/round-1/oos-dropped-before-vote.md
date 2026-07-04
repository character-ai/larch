### OOS_1: [OUT_OF_SCOPE] emit_tally guard rejects post-promotion state
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, dyn-dyn-oos-aggregation
- **Severity**: important
- **Concern**: The pre-promotion sink guard still aborts when a stale or already-promoted sink is non-empty, which blocks the intended promotion retry path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: "Allow promotion path past the guard when a qualifying pool exists or ensure sinks cannot be stale at emit entry."
  - From codex-specialist-correctness: "Make emit idempotent by rebuilding vote-only sink before the guard or ignoring already-promoted aggregate identities, then re-promote"
  - From cursor-specialist-edge-cases: "Relax to `sink_count >= OOS_ACCEPTED_COUNT` only if mismatches appear in production"
  - From dyn-dyn-oos-aggregation: "The approved plan kept this guard; relaxing it to `sink_count < oos_accepted_count` (as noted in prior design review) would make promotion retries safer."

### OOS_2: [OUT_OF_SCOPE] Dead annotate branch after status grammar change
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: The old empty-stdout warning branch never runs after the status grammar changed, so the branch is dead.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: "Remove dead branch or update to new status grammar."
  - From cursor-specialist-edge-cases: "Remove dead branch or update to new status grammar"

### OOS_3: [OUT_OF_SCOPE] Duplicate security classifier can drift between design and review paths
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-oos-aggregation
- **Severity**: latent
- **Concern**: `/design` and the review path are maintaining separate security-block classifiers, so regex drift can leak security-classed items into public filing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: "Reuse voting.is_security_block_text for promotion filtering"
  - From cursor-specialist-testing: "Reuse shared voting/file_oos security classifier"
  - From dyn-dyn-oos-aggregation: "Reuse shared voting/file_oos security classifier"

### OOS_4: [OUT_OF_SCOPE] Redundant weak empty-stdout annotate test remains
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: The older empty-stdout annotate test is redundant because the newer NEXT_ACTION coverage already exercises the behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: "Merge or update old test to assert retry KVs"

### OOS_5: [OUT_OF_SCOPE] Missing review_core_body session-env integration test
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: Direct emit-tally tests do not cover review_core_body session-env propagation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: "Add review_core_body test asserting --session-env-path on emit paths"

