## Goal
Extend is_tmp_path() to accept /var/folders macOS temp paths so REASONING_FILE placed there is not demoted to fallback text.

## Implementation Plan
1. scripts/ship-pr.sh (line 41): add /var/folders/* to case pattern in is_tmp_path()
2. scripts/implement-finalize.sh (line 44): add /var/folders/* to case pattern in is_tmp_path(); update die_usage messages at lines 99, 115, 121, 126 to list /var/folders/

## Test plan
Run /relevant-checks (pre-commit + agent-lint). Confirm test-implement-finalize.sh passes.
