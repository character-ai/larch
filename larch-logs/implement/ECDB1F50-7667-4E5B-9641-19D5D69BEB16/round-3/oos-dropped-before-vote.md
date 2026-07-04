### OOS_1: [OUT_OF_SCOPE] Step 5/8 wrappers still lack signal-aware detach
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: important
- **Concern**: The Step 5/8 wrappers still lack the signal-aware detach pattern needed to survive harness idle SIGTERM, so background drivers can be killed mid-run without detach/reattach recovery.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Track as follow-up per plan open questions
  - From cursor-specialist-edge-cases: Apply the same signal-aware detach pattern in a follow-up as the plan suggests.

### OOS_2: [OUT_OF_SCOPE] Detached review loops lack an orphan cap
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: Detached plan-review loops have no explicit orphan cap, so a disowned loop can keep running and spending tokens indefinitely if the session never reattaches.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Add a bounded orphan watchdog or self-terminate when no wrapper reattaches within a configured window.

### OOS_3: [OUT_OF_SCOPE] `--read-result-env` runs before detach-marker handling
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: The `--read-result-env` path runs before detached-marker handling, so premature probes can report missing status even while the detached loop is still active and may prompt an unnecessary retry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Handle detached-marker state in the read-result-env path or document that probes must wait for reattach completion.

