## Proposed Design Outline

### Goals
- Move the `[IMPLEMENTING]` rename in `implement-bootstrap.sh` to fire ASAP after `get-issue-state.sh` validates `STATE=OPEN` / `IS_PR=false`, before any larch-logs writes or GitHub comment posting.
- Apply the new position to both `phase_tracking` resume paths: "Branch 1 resume" (sentinel rehydrate) and "Branch 2 adopt" (fresh issue adoption).

### Non-goals
- No reset-to-original-title logic on subsequent cancel/failure paths (user explicitly excluded).
- No changes to `/design` (current rename at Step 0b sub-step 5.5 is acceptable).
- No changes to `/research` or other commands.
- No new states added to `tracking-issue-write.sh` (existing `implementing` state and existing strip-one-prefix semantics suffice).
- No movement of the Preflight admission gate — its `[DESIGNED]` / managed-prefix checks already gate `/implement` before bootstrap even runs.

### Approach sketch
- In `scripts/implement-bootstrap.sh` `phase_tracking`, identify the "Branch 2 adopt" point right after `issue_state` is confirmed `OPEN` (and `issue_is_pr=false`), but before `BRANCH_SELECTED=branch-2-adopt` triggers `run_larch_log_init` and `post-tracking-issue.sh`. Insert the existing `rename_to_implementing` call there. Remove the late call near the end of `phase_tracking`.
- For "Branch 1 resume", relocate `rename_to_implementing` similarly — fire it earlier in the resume validation flow, immediately after the sentinel sanity checks pass and before further bootstrap work.
- Both moves are pure call-site relocations of the existing `rename_to_implementing` helper. Helper body, exit-code handling, and the `[DESIGNED] → [IMPLEMENTING]` prefix swap semantics in `tracking-issue-write.sh` are unchanged.

### Surfaces in scope
- `scripts/implement-bootstrap.sh` — call-site relocation of `rename_to_implementing` inside `phase_tracking` for both Branch 1 and Branch 2.
- `skills/implement/scripts/test-implement-bootstrap.sh` — regression coverage update if it asserts the rename's position relative to log_init / post-tracking-issue.
- No SKILL.md text changes expected unless documentation references the old position.

### Open questions
- Whether the existing `test-implement-bootstrap.sh` harness asserts call ordering that would break — to be confirmed during plan drafting by reading the test.
