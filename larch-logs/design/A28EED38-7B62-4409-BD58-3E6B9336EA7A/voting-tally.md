Quick mode — Claude-only plan review.

FINDING_1: Accepted — the plan's Testing strategy mis-claims that test harnesses cold-start with `write_initial_state`; in fact `scripts/test-ship-pr.sh`'s `write_state` helper hand-composes a state file missing `NO_LOGS_COMMIT`, so adding that key to `require_key` will break the harness until `write_state` is updated.
