### [rejected] FINDING_2

**Rejected subtype:** dismissed (0 YES)

### FINDING_2: process identity validation is too brittle
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-testing, codex-specialist-testing, dyn-dyn-process-safety
- **Severity**: important
- **Concern**: Process-identity validation is using a brittle mix of full-argv substring matching and fallback needles: truncated `ps` output can refuse valid cleanup, while empty or generic stored signatures can weaken the check and let distinct sessions collide.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-testing: Add unit tests for expected_signature needle pass and fail paths.
  - From codex-specialist-testing: Store a stable short needle, and add a truncated-ps regression test.
  - From dyn-dyn-process-safety: Treat an empty stored `command_signature` as invalid at write and read time; require non-empty `command_signature` before any signal, and fail closed when it is missing.
  - From dyn-dyn-process-safety: Derive `expected_signature` from the full launch argv (at minimum include the resolved `DESIGN_TMPDIR` path) and require that needle in the current command line in addition to exact `command_signature` equality.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_5: post-kill missing-pid is treated as failure
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: important
- **Concern**: After a successful kill, callers can still see `missing-pid` / `ok=False`, which makes teardown treat the kill as a refusal and leaves sidecar and log state inconsistent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Return ok=True with reason=terminated after signals, or treat post-kill missing-pid as success in callers.
  - From cursor-specialist-edge-cases: Unlink after validated kill even when post-kill identity is missing-pid.
  - From cursor-specialist-edge-cases: rm -f the sidecar in _step3_review_cleanup after wait, matching lines 433-434.
  - From cursor-specialist-edge-cases: Log refusals only for pre-signal validation failures.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** dismissed (0 YES)

### FINDING_8: kill-site audit criteria are under-evidenced
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: important
- **Concern**: Kill-site classification is not evidenced in code, docs, or tests, so future edits can add new persisted-pgid kills without identity validation and slip past review.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Commit audited kill-site classification and optional structure-test grep pins for validated kill paths.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** dismissed (0 YES)

### FINDING_9: tmpdir and sidecar reads need stricter validation
- **Reviewer(s)**: dyn-dyn-process-safety
- **Severity**: important
- **Concern**: `kill-active-leg` and sidecar reads do not apply the stricter tmpdir and file-safety checks used elsewhere, so relative or symlinked tmpdirs can redirect record handling across sessions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-process-safety: Reuse the same tmpdir validation contract as design/finalize (absolute path, no `..`, refuse symlink roots, require session marker files) before reading, unlinking, or signaling any active-leg record.
  - From dyn-dyn-process-safety: Read through an audited helper that refuses symlinks/special files (matching `scope-anchor validate` / `atomic_write` policy) and optionally re-validates immediately before signaling.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_10

**Rejected subtype:** dismissed (0 YES)

### FINDING_10: one-second start times can collide
- **Reviewer(s)**: dyn-dyn-process-safety
- **Severity**: important
- **Concern**: Identity binding only uses one-second `lstart` timestamps, so fast pid reuse can satisfy `start_time` on churny hosts before later validation rejects the wrong process.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-process-safety: Add a monotonic boot/session discriminator where the platform exposes it (for example include `etime` or a publisher nonce in the sidecar) and treat second-granularity collisions as refusal.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

