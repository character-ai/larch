### OOS_1: Active-leg JSON publish has no atomic-write step
- **Description**: Active-leg JSON publish has no atomic-write step. Scenario: The plan replaces `.active-leg-pgid` with JSON but does not require `_write_text_atomic` (already used elsewhere in implement dispatch). A torn write is likely handled as malformed and unlinked without signaling, but concurrent `_run_leg_with_timeout` callers can still last-writer-win the single slot and leave the on-disk owner/pgid detached from a still-running leg until identity-validated cleanup runs.
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/larch/implement/dispatch_leg.py
- **Phase**: design



### OOS_2: [OUT_OF_SCOPE] Fence could skip kill-active-leg when no active-leg artifact exists
- **Description**: [OUT_OF_SCOPE] Fence could skip kill-active-leg when no active-leg artifact exists. Scenario: Owner-token gating fixes cross-invocation friendly fire, but every .py larch-run exit still spawns a Python cleanup process even when no leg was published. That is extra churn on hot paths like checks and normalize-status.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/larch/state/bootstrap.py:167-177
- **Phase**: design



### OOS_3: [OUT_OF_SCOPE] Loop identity could be captured inside plan-review run at setsid
- **Description**: [OUT_OF_SCOPE] Loop identity could be captured inside plan-review run at setsid. Scenario: The Bash sidecar plus separate teardown verb adds two new artifacts and wrapper calls. The loop already enters plan-review run --new-process-group, which is the natural point to snapshot pid/pgid/start/cmd before any child work.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/larch/review/plan_review.py:320-357
- **Phase**: design



### OOS_4: [OUT_OF_SCOPE] Active-leg JSON publish has no atomic-write step
- **Description**: [OUT_OF_SCOPE] Active-leg JSON publish has no atomic-write step. Scenario: Concurrent leg publishers can leave a partial JSON file; owner-token consume paths fail closed, so this is hardening rather than a demonstrated kill vector.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: correctness
- **Location**: python/larch/implement/dispatch_leg.py:86-93
- **Phase**: design



