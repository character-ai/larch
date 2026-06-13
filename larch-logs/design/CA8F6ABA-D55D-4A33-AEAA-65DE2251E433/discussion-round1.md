## Decision 1: Fix scope — all three root causes
- **Question**: Should we implement all three fixes (RC-1 write-once, RC-2 RECOVERY_BRANCH, RC-3 idempotency)?
- **Resolution**: Yes. The issue is URGENT and all three RCs contribute to the false-failed-publish symptom. RC-1 is defense-in-depth; RC-2 improves diagnosability; RC-3 prevents the race entirely.
- **Source**: codebase + issue label

## Decision 2: RC-1 fix location — `design-publish.sh`
- **Question**: Where does the write-once guard go? The issue names `persist_design_log_metadata`, but that function writes `.design-log-publish-metadata.env`, not `.design-publish-result.env`.
- **Resolution**: The guard belongs in `write_result_env_and_emit` inside `skills/design/scripts/design-publish.sh` (line 347). Before calling `phase_driver_write_result_env`, check whether `.design-publish-result.env` already contains `PUBLISH_OK=true`; if so and the new result is `PUBLISH_OK=false` (concurrent failure), skip the overwrite.
- **Source**: codebase

## Decision 3: RC-2 fix location — `scripts/design-log-publish.sh`
- **Question**: Scope of the REMOTE_BRANCH_EXISTS change.
- **Resolution**: Remove the `REASON==pause` gate around the fetch/show-ref block (lines 242–247). Also remove the `REASON==pause` condition from the `RECOVERY_BRANCH` emission (line 251). This is the exact diff the issue provides.
- **Source**: codebase

## Decision 4: RC-3 idempotency check location — `scripts/design-log-publish.sh`
- **Question**: Should RC-3 go in `design-step5c.sh`, `design-publish.sh`, or `design-log-publish.sh`?
- **Resolution**: `design-log-publish.sh` is the right place because `WT_BRANCH` is already computed there, REPO_ROOT and ORIGIN_DEFAULT are already resolved, and the concurrent-guard is already there. After the RC-2-fixed remote-branch fetch, check `git merge-base --is-ancestor origin/$WT_BRANCH origin/$ORIGIN_DEFAULT`; if true, the run already succeeded — emit `PUBLISH_OK=true` and exit 0 cleanly.
- **Source**: codebase
