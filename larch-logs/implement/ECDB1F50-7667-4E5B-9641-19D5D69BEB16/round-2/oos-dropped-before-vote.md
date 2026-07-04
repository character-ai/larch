### OOS_1: [OUT_OF_SCOPE] detached loops lack an orphan cap
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: Detached loops can keep running after session death without an orphan cap, leaving vendor spend and cleanup responsibility open-ended.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Document bound or add follow-up orphan teardown

### OOS_2: [OUT_OF_SCOPE] Step 5/8 detach behavior remains unhandled
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: Implement Step 5/8 still lacks signal-aware detach treatment, so a stop can kill mid-run implement drivers outside the Step 3 scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Track follow-up per plan open questions
