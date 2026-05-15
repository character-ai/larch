## Goal
Surface insufficient-voter warning through review-core.sh

## Implementation Plan

Goal: Surface the tally-votes.sh insufficient-voter warning through review-core.sh.

Root cause: review-core.sh calls tally-votes.sh with > "$tally_out", so emit()
output goes into the file. But the warning is plain text, not a KV pair, so
kv_get cannot read it and review-core.sh never sees it.

Files to modify:
1. skills/review/scripts/tally-votes.sh (line 68)
   - Change: emit "**⚠ Voting skipped..."
   - To:     emit_kv VOTING_SKIPPED_WARNING "**⚠ Voting skipped..."
   Rationale: converts the warning to a KV pair that kv_get can parse.

2. skills/review/scripts/review-core.sh (after line 256)
   - Add after reading accepted_file:
       voting_skipped_warning=$(kv_get "$tally_out" VOTING_SKIPPED_WARNING)
       [[ -n "$voting_skipped_warning" ]] && emit "$voting_skipped_warning"
   Rationale: reads the new KV key and re-emits it so users see the warning.

3. skills/review/scripts/tally-votes.md
   - Update stdout description to document VOTING_SKIPPED_WARNING key.

4. skills/review/scripts/review-core.md
   - Update stage 3 description to mention warning re-surfacing.

Testing: existing test-tally-votes.sh assertions check for the substring
"Voting skipped (N voter(s) available" which still appears in the new
emit_kv output (as part of the value). Run /relevant-checks to verify.

## Test plan
(no test plan section in plan-file)
