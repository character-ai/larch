### OOS_1: Pre-rebase merge-loop flushes still treat `commit-failed` as warn-only via `REFRESH_SKIP_MERGE_OK`
- **Description**: Pre-rebase merge-loop flushes still treat `commit-failed` as warn-only via `REFRESH_SKIP_MERGE_OK`. Scenario: Post-ensure flush+push is hardened, but later pre-rebase refreshes on CI-fix/rebase paths still allow squash-merge without a newer log commit if that flush fails to commit. Straight-merge happy path is covered; rebase-heavy paths retain a narrower stale-snapshot window.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: python/ship.py:1675-1693
- **Phase**: design
