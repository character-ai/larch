## Decision 1: Scope of fixes
- **Question**: Is fix #2 (bounded retry in postmerge-push-watch before declaring emergency-repair) in scope?
- **Resolution**: Both fix #1 (relaunch re-verify) and fix #2 (bounded auto re-run) are in scope. Doc drift sweep and tests included.
- **Source**: user

## Decision 2: SHA lookup for re-verify
- **Question**: Should re-verify key on MAIN_REPAIR_RUN_ID or the latest push run for the merged SHA?
- **Resolution**: Use MAIN_REPAIR_HEAD (merged SHA) as head_sha in read_main_health. Picks up re-runs by any run ID automatically via _classify_runs latest-first logic.
- **Source**: codebase

## Decision 3: Flap detection bypass
- **Question**: How to handle _same_sha_failure_flap returning "fail" even after a successful re-run (prior failure + latest success)?
- **Resolution**: Add skip_flap_check: bool = False to MainHealthQuery. Set True in the emergency-repair re-verify (fix #1) and in the post-rerun wait when transient_retries > 0 (fix #2). Normal paths unaffected.
- **Source**: codebase

## Decision 4: Retry bound for postmerge push-watch
- **Question**: How many re-run attempts before giving up and entering emergency-repair?
- **Resolution**: 1 attempt. Add MAIN_HEALTH_MAX_TRANSIENT_RETRIES = 1 to config.py.
- **Source**: user

## Decision 5: Independence from #6609
- **Question**: Is the driver-side fix worth doing independently of the flaky harness fix (#6609)?
- **Resolution**: Yes. These are independent: #6609 fixes the awk-truncation test flake; this issue fixes the ship driver's recovery logic. Both help; both can merge independently.
- **Source**: codebase
