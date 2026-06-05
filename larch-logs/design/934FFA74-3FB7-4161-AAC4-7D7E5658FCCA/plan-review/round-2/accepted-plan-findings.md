### FINDING_1: Folded sentinel tests do not enforce before-pause ordering
- **Reviewer(s)**: Cursor-Arch, Cursor-dyn-test-assertion-mapping
- **Severity**: important
- **Concern**: The planned folded-sentinel assertions only verify host-fence mapping, not that absorbed sentinel writes occur before the pause check. A sentinel write could be placed after `design-pause-save.sh`, allowing pause/resume to replay completed work while tests still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Extend assert_folded_sentinel_writes to assert source-env → folded write → pause-check ordering for every absorbed prior-step sentinel host fence, mirroring the step-6 after-pause/before-cleanup special case
  - From Cursor-dyn-test-assertion-mapping: Require extracted host-fence bodies and awk line-order checks (pause line after each absorbed write) for every folded step except the documented step-6 exception pattern


### FINDING_2: Zero-sketch HARD branch lacks a pinned folded sentinel write site
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The HARD zero-sketch degraded branch must mark `step-2a` and `step-2a.5` complete before jumping to Step 2b, but the plan removes the existing Step 2a success-boundary write without pinning a replacement host Bash fence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Pin item 6 to a concrete fence in the zero-sketches guard (new small Bash block before the jump to Step 2b) and add a matching assert_folded_sentinel_writes row for that degraded path


### FINDING_4: Step 1e completion is not folded into the direct Step 3 route
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Concern**: Step 1e is folded only into Step 2a even though post-plan Gate A can route directly to Step 3. A pause on that route could save `STEP=1e` and resume by replaying Gate A instead of continuing to review.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Fold .completed/step-1e into the Step 3 entry fence as well, before its pause-check, or retain a boundary-local Step 1e write on the post-plan Ready for review path; add a pause/resume test for that route


### FINDING_5: Step 1d.5 brainstorm work is treated as discussion-only despite external Bash paths
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Concern**: The plan deletes the Step 1d.5 prelude while assuming it is pure discussion, but brainstorm can launch and collect external Bash work whose fences lack equivalent pause-save handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Exclude Step 1d.5 from the deleted-prelude fold, or add an equivalent pause-save check before the first brainstorm launch/collection path; update the deleted-prelude test guard to allow the retained 1d.5 boundary.


### FINDING_6: Required script sibling contract docs are missing from the plan
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: The plan changes script behavior but does not include required sibling `.md` updates for affected scripts, leaving documented contracts stale.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Update the plan to include UPDATED entries for scripts/design-pause-load.md, scripts/test-design-structure.md, and skills/design/scripts/test-design-pause-resume.md documenting only the new folded discussion and pause-marker-clear contracts


### FINDING_7: Pause-load regression may not prove `.pause-requested` restoration and clearing
- **Reviewer(s)**: Cursor-dyn-pause-load-contract
- **Severity**: important
- **Concern**: The proposed regression can pass without exercising a restored `.pause-requested` marker, because it only requires absence after load and could use a snapshot that never contained the marker.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-pause-load-contract: Build the snapshot via `design-pause-save.sh` (stub publish copies the tmpdir while `.pause-requested` still exists: `scripts/design-log-publish.sh:294-302` excludes it only when `REASON != pause`; save removes it only after publish at `scripts/design-pause-save.sh:318`) and assert `[[ -f "$SNAPSHOT_ROOT/larch-logs/design/$RUN_ID/.pause-requested" ]]` before calling load### OOS_1:
- **Description**: Plan changes design-pause-load.sh to rm restored .pause-requested but does not update the sibling contract doc. Scenario: Future readers of design-pause-load.md will miss the post-restore clear behavior and may reintroduce the immediate re-pause loop
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: scripts/design-pause-load.md:14-40
- **Phase**: design


