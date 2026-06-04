### FINDING_1: Auto-repair shared-handler rewrite exceeds SIMPLE scope
- **Reviewer(s)**: Cursor-Arch, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Codex-dyn-contract-drift
- **Severity**: important
- **Concern**: The proposed shared handler adds prompt-side or silent auto-repair/re-publish behavior that expands a mechanical validation-fold change, risks changing reviewed plan artifacts after approval, and should remain prompt-mediated or deferred.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Ship fold + exit 4 + --skip-validate + review_budget removal first; defer auto-repair and keep the existing 3-option handler with Step 5c Override → --skip-validate
  - From Codex-Innovation: Keep the existing shared handler shape; only add the Step 5c exit-4 routing and make the existing Override path call design-publish.sh --skip-validate for composed-plan publish
  - From Cursor-Pragmatic: Ship fold exit 4 and review_budget removal first; defer handler rewrite
  - From Codex-Pragmatic: Keep the existing prompt-first handler shape, or limit the change to root-cause display plus user-approved fix/accept/cancel; do not auto-edit plan artifacts in this PR
  - From Codex-dyn-contract-drift: For SIMPLE, keep the folded driver and exit-4 hand-back but retain a prompt-mediated Fix/Override/Cancel path or require confirmation before publishing any Step 5c auto-repair


### FINDING_2: Step 5c retry result is not normalized after exit 4
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Codex-Innovation, Codex-dyn-handoff-control
- **Severity**: important
- **Concern**: If exit-4 repair or accept re-runs `design-publish.sh`, Step 5c must replace the original publish rc/output/result-env state with the retry result before final summary emission, sentinel writing, footer handling, cleanup, or cancellation decisions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Specify that handler success re-enters the publish parse fence and items 5–7, or loops the design-publish invoke until rc is not 4
  - From Codex-Arch: Make the rc4 branch a retry loop around design-publish.sh: after auto-repair or --skip-validate accept, replace _publish_out and _publish_rc with the retry result, parse the latest .design-publish-result.env through the same file-first path, then continue only when the retry rc is 0, 1, or 3; cancel exits without items 5-7
  - From Codex-Innovation: Do not publish inside the shared handler; have it repair composed-plan.md and return to one outer design-publish.sh invocation, or explicitly require the retry to replace _publish_rc, _publish_out, and parsed result state before falling through to Step 5c items 5-7
  - From Codex-dyn-handoff-control: Specify that the rc4 branch tail-calls or repeats the same design-publish capture plus file-first/stdout parse path after repair or --skip-validate accept, then continues items 5-7 only with the re-run _publish_rc and parsed result env. Cancel must exit that path before items 5-7.


### FINDING_3: Publish-tail order misplaces reentry marker
- **Reviewer(s)**: Codex-Arch, Codex-Requirements
- **Severity**: important
- **Concern**: The plan text describes or implies writing the design reentry marker before successful publish/rename, conflicting with the existing marker-after-publish contract and risking false completed reentry state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Remove the parenthetical order or correct it to the current contract: plan-block-write, diagrams upsert, design-log-publish, final summary render, [DESIGNED] rename, then design_reentry_marker_write; keep the tail otherwise unchanged
  - From Codex-Requirements: Preserve the existing code order and update the plan/docs wording to say plan-block-write -> upsert -> log publish -> post-publish summary -> rename -> design_reentry_marker_write


### FINDING_4: Folded validator invoke lacks set +e capture
- **Reviewer(s)**: Cursor-Edge, Cursor-Requirements, Cursor-Innovation, Cursor-Pragmatic, Cursor-dyn-handoff-control
- **Severity**: important
- **Concern**: Running `invoke-plan-validator.sh` under `set -euo pipefail` can abort before parsing `VALIDATE_*` or writing the expected result env, turning validator defects or infra failures into unclassified shell exits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge, Cursor-Requirements: Mirror design-postplan-emit.sh: set +e around invoke-plan-validator.sh capture, parse KVs, then branch defects-found (exit 4) vs infra (fail exit 2)
  - From Cursor-Innovation: Wrap the folded invoke-plan-validator.sh call in set +e; parse stdout; branch on VALIDATE_STATUS=defects-found vs empty/not-run vs rc!=0 exactly like design-postplan-emit.sh
  - From Cursor-Pragmatic: Mirror design-postplan-emit.sh set +e capture parse then branch exit 4 vs exit 2
  - From Cursor-dyn-handoff-control: Wrap invoke-plan-validator in set +e; branch on VALIDATE_STATUS like design-postplan-emit


### FINDING_5: Shared validator handler omits Step 3 defects path
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Concern**: The proposed shared handler covers Step 2b, Gate B, discussion round 2, and Step 5c, but not the existing Step 3 `plan-review-loop` defects path, leaving its target file, log source, and continuation semantics undefined.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Add a minimal Step 3 site entry: target plan.txt, read the existing validate-plan-commands.log default, revalidate via design-postplan-emit.sh, then preserve the current Step 3 Gate-B-bypass continuation to Step 3b.


### FINDING_6: Redaction pipeline nonzero failures are not mapped to exit contract
- **Reviewer(s)**: Codex-Edge, Codex-Innovation, Codex-Requirements
- **Severity**: important
- **Concern**: Moving redaction into `design-publish.sh` without explicit nonzero handling can let `redact-secrets.sh`, pipeline, or redirection failures exit with arbitrary raw statuses and no clear result contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Wrap the redaction command in an if ! pipeline; on failure call fail "redact-secrets.sh failed", then keep the planned non-empty redacted-file check.
  - From Codex-Innovation: Wrap the redaction pipeline in an explicit if ! ...; then fail 'redact-secrets.sh failed'; fi block, then separately check the redacted file is non-empty before publishing
  - From Codex-Requirements: Wrap redaction with if ! redact-secrets.sh ...; then fail 'redact-secrets.sh failed'; fi before the non-empty check, and add a test-design-publish case asserting rc 2 and no publish on redactor failure


### FINDING_7: Step 5c still treats rc 4 as unexpected/fatal
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-dyn-handoff-control
- **Severity**: important
- **Concern**: The Step 5c driver contract, guard, or structure pins still hardcode `{0,1,3}`, so folded validation exit 4 may abort before the shared handler or fail structural tests after the contract is widened.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Widen contract to {0,1,3,4}; document exit 4 handler routing; insert handler prose before items 5-7
  - From Cursor-dyn-handoff-control: Widen guard to include 4; add explicit rc==4 branch that parses VALIDATE_* and runs shared handler before items 5-7
  - From Cursor-dyn-handoff-control: Extend plan to retarget 1348/1374 and driver contract text to {0,1,3,4}


### FINDING_8: Step 5c parse fence omits VALIDATE_* keys
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-dyn-handoff-control
- **Severity**: important
- **Concern**: The result-env parsing path does not load validator status/log/count keys, so an exit-4 handler may not have the defect context it needs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add VALIDATE_STATUS and four sibling keys to result-env parse case arms
  - From Cursor-dyn-handoff-control: Add VALIDATE_* keys to file-first/stdout parse before shared handler


### FINDING_10: Quick/force validation removal lacks stale-contract pins
- **Reviewer(s)**: Cursor-Pragmatic, Codex-dyn-harness-oracle
- **Severity**: important
- **Concern**: Planned test/doc changes remove quick-skip or force-validation pins without adding absence checks, so stale `review_budget`, `skipped-quick`, or `--force-validate` contracts can survive and mislead orchestration.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Repin assertion to unconditional validation contract not quick-skip owner
  - From Codex-dyn-harness-oracle: Add narrow absent checks in test-design-structure.sh for --force-validate, skipped-quick, and review_budget quick/full in the affected design docs and SKILL helper prose where the plan says those contracts are removed


### FINDING_13: Postplan tests do not catch legacy review_budget=quick
- **Reviewer(s)**: Codex-dyn-harness-oracle
- **Severity**: important
- **Concern**: Removing quick-skip coverage without adding a legacy `review_budget=quick` assertion can allow the old reader/skip branch to remain while new fixtures still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-harness-oracle: Add one legacy fixture with review_budget=quick that expects the validator stub to run and VALIDATE_STATUS=ok, or add a structure assertion that REVIEW_BUDGET, skipped-quick, and --force-validate are absent from design-postplan-emit.sh


### FINDING_14: Run-params tests do not assert review_budget removal
- **Reviewer(s)**: Codex-dyn-harness-oracle
- **Severity**: important
- **Concern**: Planned run-params harness changes can pass while the writer still emits `review_budget:null` or accepts the removed `--review-budget` flag, leaving schema-version drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-harness-oracle: Add jq assertions that has("review_budget") is false for emitted JSON, and add an argv rejection case for --review-budget full as an unknown flag

