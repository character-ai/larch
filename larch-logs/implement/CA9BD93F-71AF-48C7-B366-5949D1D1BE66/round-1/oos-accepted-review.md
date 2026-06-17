### OOS_1: [OUT_OF_SCOPE] _restore_finalize read-key abort under set -e
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `_restore_finalize` uses bare `session read-key` calls without `|| true` or default fallbacks under active `set -e`. A malformed `ship-pr-state.sh` / `finalize-state.sh` that makes `read-key` exit 1 can abort finalize before `clear-implement-pointer` and teardown. Copied from deleted `step-18-finalize.sh`, not introduced here.
- **Suggested revisions (informational for voters; coder decides)**:


