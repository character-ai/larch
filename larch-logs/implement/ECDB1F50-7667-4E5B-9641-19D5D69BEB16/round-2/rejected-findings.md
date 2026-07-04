### [rejected] FINDING_2

**Rejected subtype:** dismissed (0 YES)

### FINDING_2: detach state can fail open before loop identity is proven
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: important
- **Concern**: Signal-driven cleanup and reattach/disown handling can run before loop identity is established or validated, so a stale sidecar, marker-publication failure, or reattach failure can leave a live loop running while clearing state and allowing duplicate dispatch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Defer destructive cleanup until current loop identity is known, or record a pending signal and detach after identity is verified.
  - From cursor-specialist-edge-cases: Clear or validate sidecar before launch; set identity_ready only when sidecar pid equals _loop_pid
  - From cursor-specialist-edge-cases: Teardown or fail closed before marker cleanup; block fresh dispatch until identity validation reports gone
  - From cursor-specialist-edge-cases: Make marker publication fail-closed, verify the regular marker and expected PID before disown, otherwise teardown/sweep or emit a terminal recovery failure


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

