## Goal
Fix scoreboard.sh awk partial-substring match bug so reviewer labels like "Correctness" do not accidentally match "Codex-Correctness" entries.

## Implementation Plan

Files to modify:
1. `skills/shared/scripts/scoreboard.sh` line 34: change `$0 ~ label` to `$0 ~ "REVIEWER=" label " "`
2. `skills/shared/scripts/test-scoreboard.sh`: add regression test for partial-match case

## Test plan
Run `make test-scoreboard` to verify the fix and new regression test pass.
