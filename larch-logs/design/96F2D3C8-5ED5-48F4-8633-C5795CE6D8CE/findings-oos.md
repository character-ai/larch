### OOS_1: Pre-rebase merge-loop flushes still treat `commit-failed` as warn-only via `REFRESH_SKIP_MERGE_OK`
- **Description**: Pre-rebase merge-loop flushes still treat `commit-failed` as warn-only via `REFRESH_SKIP_MERGE_OK`. Scenario: Post-ensure flush+push is hardened, but later pre-rebase refreshes on CI-fix/rebase paths still allow squash-merge without a newer log commit if that flush fails to commit. Straight-merge happy path is covered; rebase-heavy paths retain a narrower stale-snapshot window.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: python/ship.py:1675-1693
- **Phase**: design



### OOS_2: NEVER #16 still describes speculative `OUTCOME=merged` pre-squash as a future need
- **Description**: NEVER #16 still describes speculative `OUTCOME=merged` pre-squash as a future need. Scenario: Plan deliberately records `pr-created` (minimum acceptable per issue) and does not update the skill contract prose to document the post-ensure `pr-created` flush pattern actually being implemented.
- **Reviewer**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: architecture
- **Location**: skills/implement/SKILL.md:NEVER #16
- **Phase**: design



### OOS_3: NEVER #16 still describes speculative `OUTCOME=merged` as a future need
- **Description**: NEVER #16 still describes speculative `OUTCOME=merged` as a future need. Scenario: The plan implements option (2) (`pr-created` pre-squash) and explicitly defers option (1), but does not update the SKILL contract that still points operators at an unimplemented speculative-merged flush.
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/implement/SKILL.md:NEVER-16
- **Phase**: design



