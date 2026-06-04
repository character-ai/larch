### FINDING_1:
- **Reviewer(s)**: Codex-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/SKILL.md:465-466
- **Concern**: Plan misses adjacent runtime prose that still says Step 5c [DESIGNED] rename uses the same publish guard. Scenario: After the PR, SKILL.md would contain contradictory instructions: Step 5c says rename is no longer PUBLISH_OK-gated, while Step 0b still describes Step 5c as publish-gated
- **Proposed resolution**: Update the Step 0b clarify prose to say Step 5c reserves --state designed until Gate C plus composed plan/plan write, and that the Step 5c rename is no longer PUBLISH_OK-gated

### FINDING_2:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:465
- **Concern**: The plan updates Step 5c prose but leaves Step 0b saying the [DESIGNED] rename is still behind “the same publish guard.”. Scenario: After the PR, the shipped /design prompt would contain contradictory gate rules, which can lead future edits or prompt-side interpretation to preserve or reintroduce the removed PUBLISH_OK gate and defeat early /implement admission.
- **Proposed resolution**: Add this SKILL.md sentence to the planned edits: remove “and the same publish guard” and state that --state designed is reserved for Step 5c after Gate C and the composed larch:plan/OOS flow, while the Step 5c [DESIGNED] rename itself is no longer PUBLISH_OK-gated.

### FINDING_3:
- **Reviewer(s)**: Cursor-dyn-contract-sync
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/design/SKILL.md:465
- **Concern**: Clarify sub-step 5 still documents `--state designed` under the same publish guard as Step 5c. Scenario: After the driver change, maintainers reading Step 0b believe `[DESIGNED]` still requires `PUBLISH_OK=true`, contradicting the new `SESSION_ID`-only rename gate and the updated Step 5c item 6
- **Proposed resolution**: Add a third SKILL.md edit in the plan: replace “same publish guard” with prose that Step 5c renames to `[DESIGNED]` after diagram upsert when `SESSION_ID` is non-empty, without waiting on `design-log-publish.sh`

### FINDING_4:
- **Reviewer(s)**: Codex-dyn-contract-sync
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:461-466
- **Concern**: Step 0b clarify prose would still say Step 5c [DESIGNED] rename uses the same publish guard. Scenario: After the proposed change, design-publish.sh renames on SESSION_ID only while the marker and cleanup stay PUBLISH_OK-gated; this prompt text preserves the old publish-gated contract and could cause a future edit to restore the wrong gate
- **Proposed resolution**: Update this SKILL.md sentence too: remove "and the same publish guard" and state that only the clarify-path [DESIGNING] rename is PUBLISH_OK-gated; Step 5c [DESIGNED] rename runs after plan/upsert when SESSION_ID is non-empty

### FINDING_5:
- **Reviewer(s)**: Codex-dyn-contract-sync
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/design/references/approval-gates.md:179-181
- **Concern**: Gate C approval text still lists finalization as design-log-publish.sh then rename tracking issue. Scenario: This mandatory Gate C reference would keep user-facing prompt prose describing the old publish-before-rename order after the driver changes
- **Proposed resolution**: Rename this one-line option summary to avoid ordering drift, e.g. "run the design-publish.sh tail" or list the new order with rename before design-log-publish

### FINDING_6:
- **Reviewer(s)**: Cursor-dyn-admission-gate
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/SKILL.md:1550-1553 skills/design/scripts/render-final-summary.sh:300-314 plan.txt:54-55
- **Concern**: Plan fixes script admission (early rename) but explicitly leaves failed-publish operator prose unchanged. Scenario: After reorder, publish can fail once the issue is already [DESIGNED] and larch:plan is on the body; Step 5d still prints only log publish incomplete and append_failed_publish_notes still says recover the flush PR before treating logs as complete, with no /implement admission note
- **Proposed resolution**: When PUBLISH_OK=false, extend the Step 5d footer (and optionally append_failed_publish_notes) with one line that /implement Preflight admits on the [DESIGNED] title and is not blocked by log flush failure; keep Step 6 cleanup publish-gated

### FINDING_7:
- **Reviewer(s)**: Codex-dyn-admission-gate
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/implement-admission.md:17; skills/design/SKILL.md:465-466
- **Concern**: Admission-facing prose still ties the [DESIGNED] transition to successful publish / the same publish guard.. Scenario: After the proposed early rename succeeds and design-log-publish later emits PUBLISH_OK=false, scripts/implement-admission.sh remains title-keyed and can admit /implement, but these prose contracts still tell operators or future maintainers that [DESIGNED] waits for publish success.
- **Proposed resolution**: Add a minimal doc/prose update: say [DESIGNED] is written after Gate C, OOS filing, composed larch:plan write, and diagram upsert; design-log-publish success, cleanup, and reentry-marker creation are not /implement admission prerequisites.
