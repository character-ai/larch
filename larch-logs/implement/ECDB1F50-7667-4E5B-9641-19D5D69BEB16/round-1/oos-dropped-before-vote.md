### OOS_1: [OUT_OF_SCOPE] Detached signal handling lacks abort/orphan control
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, dyn-dyn-signal-lifecycle
- **Severity**: latent
- **Concern**: TERM/HUP/INT all flow through the same detach path, so deliberate TaskStop is indistinguishable from harness idle-kill, and there is still no orphan cap when nothing reattaches. That can leave detached loops and reviewer dispatches running unattended indefinitely.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From dyn-dyn-signal-lifecycle: Address the concern above.

### OOS_2: [OUT_OF_SCOPE] Implement wrappers still rely on harness-stoppable EXIT traps
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-signal-lifecycle
- **Severity**: latent
- **Concern**: The `/implement` Step 5 and Step 8 wrappers still use EXIT traps without detach/reattach semantics, so idle harness kills can terminate long review/ship drivers mid-run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From dyn-dyn-signal-lifecycle: Address the concern above.

### OOS_3: [OUT_OF_SCOPE] Await-loop identity coverage is still too thin
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-signal-lifecycle
- **Severity**: important
- **Concern**: The new `await_loop_identity_main` path and the Bash/Python reattach boundary still lack direct test coverage for timeout, missing-pid, stale-env rejection, and registry wiring. Those regressions would otherwise only surface through the integration harness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From dyn-dyn-signal-lifecycle: Address the concern above.

