### OOS_1: [OUT_OF_SCOPE] Reattach normalize failure emits no stdout stall envelope
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: latent
- **Concern**: Reattach normalize failures may emit no stdout stall envelope, relying on the detached-marker carve-out before preflight-failure routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Document or emit minimal stall envelope if orchestrator ordering cannot be guaranteed

### OOS_2: [OUT_OF_SCOPE] Broad argv substring matching still widens kill scope
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: latent
- **Concern**: Broad argv substring matching leaves the tmpdir kill scope wider than intended.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Tighten matching in a dedicated hardening change

### OOS_3: [OUT_OF_SCOPE] Pre-identity TERM harness lacks child-exit assertion
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: The pre-identity TERM harness does not assert that the fake child process exits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Assert fake child PID is gone after TERM path

### OOS_4: [OUT_OF_SCOPE] Orphan cap is only checked at loop boundaries
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: The orphan cap is only checked at loop boundaries, so a long in-flight round can run past 7200 seconds until the next boundary.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Accepted plan trade-off; optional mid-round watchdog if spend becomes material

