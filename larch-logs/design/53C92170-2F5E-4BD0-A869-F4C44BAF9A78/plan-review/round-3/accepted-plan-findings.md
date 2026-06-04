### FINDING_1: Volatile-only cleanup must fail closed
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Concern**: Volatile-only skip handling can silently proceed after failed restore/clean/reset or leftover dirty worktree state, risking later stalled force-push behavior or partial index/worktree races.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: After each git restore/clean/reset, require returncode==0 or raise ShipError; after cleanup call git.status_porcelain(repo-wide); if stdout non-empty raise ShipError with the porcelain snippet (maps to JSON STALLED via #4). Do not treat failed cleanup as a no-op success


### FINDING_3: Real or recorded gh pr create coverage is required
- **Reviewer(s)**: Cursor-dyn-acceptance-test-gap
- **Severity**: important
- **Concern**: Stub-only `gh pr create` tests would not catch the original real-CLI failure caused by unsupported `--json`; the acceptance gate needs real CLI or recorded transcript coverage that verifies `--json` is absent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-acceptance-test-gap: Add one integration test that either shells out to `gh` when available or replays a recorded `gh pr create` transcript and asserts rc=0 resolution without `--json` in argv; keep the stub cases as fast regression but not as the sole #3 gate### OOS_1:
- **Description**: Parallel issue #3446 may edit OUTCOME_EXIT_MAP while this plan assumes STALLED stays EXIT_STALLED (4). Scenario: Merge or rebase order could land a #3446 change that remaps Outcome.STALLED or drops the key; main() would return a non-4 exit while tests still expect 4 only if this branch’s test_ship.py pin wins review
- **Reviewer**: Cursor-dyn-stdout-contract
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: python/config.py:18-23
- **Phase**: design


