# Review Round 5

- Mode: `diff`
- 6 accepted, 12 rejected (12 exonerated)

## Accepted Findings

### FINDING_10: Successful restore can resume while stale pause marker remains
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-ship-resume-output.txt, dyn-route-contract-output.txt
- **Severity**: important
- **Concern**: `LOAD_OK=true` with `MARKER_CLEARED=false` permits `resume@*` while the issue marker remains live, causing later `/design` invocations to reload stale snapshots or clobber newer tmpdir work without loud operator guidance.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-ship-resume-output.txt: Address the concern above.
  - From dyn-route-contract-output.txt: Address the concern above.


### FINDING_13: Non-retryable pause-load failures keep stale markers
- **Reviewer(s)**: dyn-ship-resume-output.txt
- **Severity**: important
- **Concern**: `emit_load_fail` keeps markers even for permanent validation or binding failures that retrying cannot fix, leaving operators stuck in repeated fail/fallthrough cycles unless they manually edit the marker.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ship-resume-output.txt: Address the concern above.


### FINDING_25: Remote recovery FETCH_HEAD test does not assert restored result
- **Reviewer(s)**: dyn-harness-realism-output.txt
- **Severity**: important
- **Concern**: The remote-recovery `FETCH_HEAD` harness checks git stub calls but not `LOAD_OK=true`, restored artifacts, `.resume-loaded`, or marker lifecycle, so wrong ref extraction could pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-realism-output.txt: Address the concern above.


### FINDING_28: Local recovery branch test does not assert restored result
- **Reviewer(s)**: dyn-harness-realism-output.txt
- **Severity**: latent
- **Concern**: The local recovery branch case checks fetch behavior but not `LOAD_OK=true` or restored artifact presence, allowing a broken local restore path to pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-realism-output.txt: Address the concern above.


### FINDING_8: Missing route integration test for successful paused resume with lifecycle title
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: There is no `design-route.sh` integration test proving `[DESIGNING]` title plus valid pause marker and successful restore routes to `resume@STEP` instead of title cancellation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_9: `LOAD_OK=false` pause loads fall through to normal routing
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-ship-resume-output.txt, dyn-route-contract-output.txt
- **Severity**: important
- **Concern**: When a pause marker is present and loader restore fails, `design-route.sh` can fall through to title filtering, `proceed`, or `already-planned` while the marker remains. This obscures pause-load failure guidance and can start fresh design work with a stale auto-resume pointer.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-ship-resume-output.txt: Address the concern above.
  - From dyn-route-contract-output.txt: Address the concern above.


