### OOS_1: [OUT_OF_SCOPE] Step 6 change-detection stalls classified as unrecoverable because `STALL_STEP=7`
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: important
- **Concern**: `_step6_entry_seed_stall` seeds `STALL_STEP=7` with `bail_reason=review-change-detection-failed`, while `stall_recovery._classify_text` only maps step `"6"` (not `"7"`) to the `contract-failure` bucket. Change-detection stalls therefore fall through to generic `unrecoverable` classification instead of the step-6 contract path. This matches the SKILL invalid-envelope `STALL_STEP=7` contract and tests pin `stall_step="7"`; both paths end with `RESUME_HINT=none`, so automatic recovery behavior is unchanged.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_2: [OUT_OF_SCOPE] Unallowlisted `review-change-detection-failed` bail token is reporting-only
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: important
- **Concern**: `review-change-detection-failed` is not in `STALL_RECOVERY_BAIL_REASON_TOKENS`, so stall reports may sanitize that bail token. Reporting polish only; the durable state is still written and Step 18 routing works.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_3: [OUT_OF_SCOPE] Pre-existing composite envelope on failed 7.r after successful commit leg
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: `checks_commit_route_main` can return non-zero while emitting `NEXT_ACTION=continue` when `7.r` fails after a successful commit leg. Pre-existing composite behavior, not introduced by the Step 6 fold; the old separate Step 6 `checks-commit-route` launcher had the same envelope shape.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_4: [OUT_OF_SCOPE] Missing explicit `_MACHINE_STDOUT_KEYS` membership assert for step-6-entry
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: Plan called for an explicit `_MACHINE_STDOUT_KEYS` membership assert for implement step-6-entry; only the quiet-disable case was added. Drift between plan and tests is harder to audit; a future refactor could drop the frozenset entry while leaving the quiet case unless someone reads cli.py directly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add assert ("implement", "step-6-entry") in cli._MACHINE_STDOUT_KEYS alongside the registry assert in test_cli.py or test_implement_dispatch.py.

### OOS_5: [OUT_OF_SCOPE] Structure harness lacks forbid pin for bare Step 6 repair `checks-commit-route`
- **Reviewer(s)**: cursor-specialist-testing, dyn-dyn-step6-routing
- **Severity**: nit
- **Concern**: Plan asked to forbid bare `checks-commit-route` on Step 6 repair re-entry; only positive `require`s were added in the structure harness and/or repair-loop prose was updated without a matching `forbid()`. A contributor could reintroduce bare `checks-commit-route --checks-site step6` in repair-loop docs and bypass `--force-checks` on repair.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add forbid(checks_ref, 'python/cli.py implement checks-commit-route --checks-site step6', ...) or pin the never re-enter bare checks-commit-route sentence.
  - From dyn-dyn-step6-routing: The plan called for forbidding bare `checks-commit-route` on Step 6 repair re-entry in the structure harness; prose in `skills/implement/references/checks-repair-loop.md:28,81` was updated, but there is no matching `forbid()` for repair-loop `checks-commit-route --checks-site step6`. Repair-loop drift is still prompt-only.

### OOS_6: [OUT_OF_SCOPE] Anti-halt markdown contract diverges from shell harness
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: The markdown contract says per-site lookback needs `REDACTED_LOG_FILE`; the shell harness still checks Checks Failure Entry Macro per site. Editors following the md could change Step 3/6 blockquotes and be surprised when the harness still demands Checks Failure Entry Macro nearby.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Align the md with the shell harness, or update the awk script to match the new REDACTED_LOG_FILE per-site rule.

### OOS_7: [OUT_OF_SCOPE] Anti-halt harness does not scan repair-loop reference for Step 6 argv
- **Reviewer(s)**: dyn-dyn-harness-pins
- **Severity**: latent
- **Concern**: Repair re-entry launchers (`--force-checks true`) live only in `checks-repair-loop.md`, so the anti-halt harness still scans `SKILL.md` alone. A regression that drops `--force-checks true` from the repair reference would not fail `EXPECTED_SITES=3`.
- **Suggested revisions (informational for voters; coder decides)**:

