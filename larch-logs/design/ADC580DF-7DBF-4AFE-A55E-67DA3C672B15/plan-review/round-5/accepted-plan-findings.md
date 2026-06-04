### FINDING_2: Folded Step 5c publish path drops the pause checkpoint
- **Reviewer(s)**: Codex-Arch, Codex-Edge, Codex-dyn-operator-retry-flow
- **Severity**: important
- **Concern**: The proposed Step 5c replacement removes the existing pause-check prelude before final validation/redaction/publish. If `.pause-requested` appears after composition or during retry flow, `design-publish.sh` may proceed to side effects instead of saving pause state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add the design-pause-save.sh prelude line to the new Step 5c design-publish.sh capture fence and every retry recapture, or add an equivalent pause checkpoint inside design-publish.sh before validation/redaction/publish
  - From Codex-Edge: Add the current pause prelude to the new design-publish attempt wrapper before every initial and retry call, or perform the same checkpoint inside design-publish.sh before validation and redaction
  - From Codex-dyn-operator-retry-flow: Keep the existing pause prelude in the new foreground Step 5c publish fence immediately before design-publish.sh, or add an equivalent pre-side-effect pause check inside design-publish.sh before validation/redaction/publish


### FINDING_3: Step 5c sentinel harness pin is missing from the retire/update list
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan changes the Step 5c sentinel gate to depend on latest `_publish_rc` in `{0,1,3}` plus `PLAN_WRITE_OK=true`, but `scripts/test-design-structure.sh` still pins the old `PLAN_WRITE_OK`-only prose and the plan’s retire list omits that pin.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: make test-design-structure fail after SKILL.md update Add 1344-1345 to the (15b) pin update list in the plan and replace the grep with prose that matches the new rc plus PLAN_WRITE_OK gate (or drop the pin if redundant)


### FINDING_4: Legacy flag no-op acceptance coverage is incomplete
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: The plan requires legacy `--review-budget full|quick` and `--force-validate` to remain accepted no-ops, but the planned tests only cover `--review-budget full` and may remove existing `--force-validate` coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add narrow legacy cases: assert scripts/write-run-params.sh --review-budget quick exits 0 and omits review_budget, and keep or rewrite one design-postplan-emit.sh --force-validate invocation that exits 0 and still validates.


### FINDING_5: Existing bad-review-budget rejection test conflicts with planned legacy no-op behavior
- **Reviewer(s)**: Cursor-dyn-legacy-flag-drift
- **Severity**: important
- **Concern**: `scripts/test-write-run-params.sh` still expects `--review-budget medium` to be rejected, but the plan changes `--review-budget` into a legacy no-op. The harness would fail after a correct implementation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-legacy-flag-drift: Add to the plan's `test-write-run-params.sh` section: remove or rewrite the `bad-review-budget` rejection case; assert exit 0 and `has("review_budget") == false` for arbitrary legacy values like `medium`


### FINDING_6: Empty review-budget test still expects a null key instead of absent key
- **Reviewer(s)**: Cursor-dyn-legacy-flag-drift
- **Severity**: important
- **Concern**: The `empty-v3-fields` jq assertion still expects `.review_budget == null` after `--review-budget ""`, but the planned jq template drops `review_budget` entirely, so the key should be absent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-legacy-flag-drift: Extend the plan's harness update: change the empty-string legacy case to assert `has("review_budget") == false` (same as the new default-write case)

