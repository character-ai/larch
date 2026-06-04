### FINDING_1: Admission prose still describes [DESIGNED] rename as publish-gated
- **Reviewer(s)**: Codex-Arch, Codex-Requirements, Cursor-dyn-contract-sync, Codex-dyn-contract-sync, Codex-dyn-admission-gate
- **Severity**: important
- **Concern**: Multiple prompt/admission prose locations still say or imply the Step 5c `[DESIGNED]` transition uses the old publish-success guard, contradicting the planned driver change where the rename can happen before `design-log-publish.sh` succeeds. This could mislead operators or future maintainers into preserving or restoring the removed `PUBLISH_OK` gate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Update the Step 0b clarify prose to say Step 5c reserves --state designed until Gate C plus composed plan/plan write, and that the Step 5c rename is no longer PUBLISH_OK-gated
  - From Codex-Requirements: Add this SKILL.md sentence to the planned edits: remove “and the same publish guard” and state that --state designed is reserved for Step 5c after Gate C and the composed larch:plan/OOS flow, while the Step 5c [DESIGNED] rename itself is no longer PUBLISH_OK-gated.
  - From Cursor-dyn-contract-sync: Add a third SKILL.md edit in the plan: replace “same publish guard” with prose that Step 5c renames to `[DESIGNED]` after diagram upsert when `SESSION_ID` is non-empty, without waiting on `design-log-publish.sh`
  - From Codex-dyn-contract-sync: Update this SKILL.md sentence too: remove "and the same publish guard" and state that only the clarify-path [DESIGNING] rename is PUBLISH_OK-gated; Step 5c [DESIGNED] rename runs after plan/upsert when SESSION_ID is non-empty
  - From Codex-dyn-admission-gate: Add a minimal doc/prose update: say [DESIGNED] is written after Gate C, OOS filing, composed larch:plan write, and diagram upsert; design-log-publish success, cleanup, and reentry-marker creation are not /implement admission prerequisites.

### FINDING_2: Gate C approval text preserves old publish-before-rename order
- **Reviewer(s)**: Codex-dyn-contract-sync
- **Severity**: latent
- **Concern**: The Gate C approval reference still describes finalization as running `design-log-publish.sh` before renaming the tracking issue, leaving mandatory user-facing prose with the old ordering after the driver changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-contract-sync: Rename this one-line option summary to avoid ordering drift, e.g. "run the design-publish.sh tail" or list the new order with rename before design-log-publish

### FINDING_3: Failed-publish footer omits that /implement admission is already unblocked
- **Reviewer(s)**: Cursor-dyn-admission-gate
- **Severity**: important
- **Concern**: The plan changes script admission by renaming earlier, but leaves failed-publish operator prose saying only that log publish is incomplete. If publish fails after the issue is already `[DESIGNED]` and the plan is present, the output does not tell operators that `/implement` admission is still allowed while cleanup remains publish-gated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-admission-gate: When PUBLISH_OK=false, extend the Step 5d footer (and optionally append_failed_publish_notes) with one line that /implement Preflight admits on the [DESIGNED] title and is not blocked by log flush failure; keep Step 6 cleanup publish-gated
