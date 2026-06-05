### [Plan Review] FINDING_2

### FINDING_2: Success-path `clear_pause_marker` lacks explicit `set -e` guard in plan
- **Reviewer(s)**: Cursor-dyn-marker-refactor-completeness
- **Severity**: important
- **Concern**: WI3’s post-success `clear_pause_marker` call is not spelled out with an explicit `set -e`-safe guard in the plan. If WI3 drops the internal `|| true` at `scripts/design-pause-load.sh:42` and adds a bare success-path call, a failed `named-block-write.sh --delete` aborts the script before `emit_kv LOAD_OK true` (currently at lines 298–306). Under `set -euo pipefail`, `design-route.sh` then sees `_pause_rc != 0` and adds `design-pause-load-failed` (`skills/design/scripts/design-route.sh:314-316`) instead of emitting `LOAD_OK=true` with `WARN=marker-delete-failed`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-marker-refactor-completeness: Spell out the success-path snippet: `if ! clear_pause_marker; then` set/append `WARN_VALUE` to `marker-delete-failed` without clobbering an existing `body-drift`; `fi` then emit `LOAD_OK=true` — same explicit `if !` style as WI2 git guards

