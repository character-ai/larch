# Review Round 3

- Mode: `diff`
- 3 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: stale pgid cleanup can signal unrelated processes
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-edge-cases
- **Severity**: important
- **Concern**: Missing-leader handling and fallback `killpg` on recorded pgids can treat a stale or recycled process group as safe, so cleanup may signal unrelated processes instead of failing closed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From codex-specialist-edge-cases: Fail closed on missing leader unless current group members have recorded identities that validate; otherwise use tmpdir-scoped cleanup instead of killpg by stale pgid.


### FINDING_2: active-leg unlink can delete a newer owner record
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: important
- **Concern**: Cleanup unlinks `.active-leg.json` after termination without confirming the file still contains the consumed owner record, so a concurrent owner can publish a new record that gets deleted and leaves the live leg untracked.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Re-read before unlink and delete only if the current JSON matches the consumed payload/owner/pid/start-time/writer fields.


### FINDING_3: fast zero-exit legs can be misreported as publication failures
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: latent
- **Concern**: A short-lived leg can exit successfully before process identity capture, causing active-leg publication to fail and mask the real successful result.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: If publication fails, drain/poll first and return the child result when already exited; only kill and fail closed for still-running untracked legs.
