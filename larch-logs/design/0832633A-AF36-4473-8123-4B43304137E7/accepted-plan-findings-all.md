### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:846-861
- **Concern**: Plan changes exit code but not Fix-and-retry recovery for skipped composition. Scenario: After rc=4 the shared handler Fix-and-retry text still says re-run design-step5c.sh only; orchestrator can skip Step 5c item 1 again and loop on missing/empty composed-plan.md instead of composing and proceeding
- **Proposed resolution**: Extend SKILL.md edits: on missing/empty composed-plan Fix-and-retry must re-run item 1 (compose composed-plan.md) then re-invoke design-step5c.sh; update line 861 (and shared handler Step 5c bullet) not only item 2




### FINDING_1: Override cannot recover missing or empty composed-plan.md
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: After routing missing-or-empty `composed-plan.md` through exit 4, the shared validator-failure prompt still documents **Override** as `design-step5c.sh --skip-validate`. `design-publish.sh` still checks `[[ -s "$DESIGN_TMPDIR/composed-plan.md" ]]` before the `--skip-validate` branch and calls `fail()` (exit 5) when the file is missing or empty. Override therefore still aborts with `failed-publish-tail` instead of recovering the session.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: For the missing-or-empty composed-plan diagnostic, restrict the Step 5c validator prompt to Fix-and-retry and Cancel only, or document that Override applies only when composed-plan.md is already non-empty with ordinary command defects; do not present Override as recovery for skipped Step 5c item 1


### FINDING_2: Shared auto-repair bypasses Step 5c item 1 composition on missing-composed-plan exit 4
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: Converting missing-or-empty `composed-plan.md` to exit 4 with `VALIDATE_STATUS=defects-found` still enters **### Plan command validator failure (shared)**, which always runs `design-step-validator-autofix.sh` against `composed-plan.md` before the operator prompt. On a missing or empty file, auto-fix may succeed and the `ok` branch re-invokes `design-step5c.sh --skip-validate` without Step 5c item 1 synthesis from `plan.txt` and acceptance artifacts. That bypasses the orchestrator composition contract (`## Plan`, `## Acceptance`, `diff_lines`) the bug fix is meant to restore.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In the shared auto-repair block, skip auto-fix when `VALIDATE_LOG_FILE` contains the missing-or-empty composed-plan diagnostic (orchestrator must compose); go straight to the operator prompt where Fix-and-retry requires Step 5c item 1 first
  - From Cursor-Innovation: In ### Plan command validator failure (shared), skip `design-step-validator-autofix` when `VALIDATE_LOG_FILE` contains the missing-composed-plan diagnostic; go straight to `AskUserQuestion` with Fix-and-retry requiring Step 5c item 1 before `design-step5c.sh`
  - From Cursor-Pragmatic: Add a matching special case in ### Plan command validator failure (shared): when `VALIDATE_LOG_FILE` contains the missing-or-empty composed-plan diagnostic skip auto-repair and go straight to the operator prompt (Fix-and-retry must run Step 5c item 1 before retrying the wrapper)


### FINDING_3: Missing-composed-plan test lacks no-side-effect guards
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The updated missing-composed-plan test (`test-design-publish.sh` lines 427–435) only asserts exit code and KVs. Unlike the adjacent validator-defects case (lines 438–454), it does not assert that redaction, plan-block write, rename, or publish stubs were not invoked. A regression that performs side effects before exit 4 would not be caught.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Mirror the defects test: assert `composed-plan.redacted.md` is absent and publish/rename stubs were not invoked


### FINDING_4:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:861,914-930
- **Concern**: [SCOPE-REDUCTION] Missing-composed-plan rc4 is routed through the ordinary Step 5c validator flow without carving out auto-repair and Override paths. Scenario: The shared handler can run cross-vendor auto-repair against an empty composed-plan.md, then re-enter Step 5c with --skip-validate and publish a synthesized plan instead of rerunning Step 5c item 1; Override also reruns design-step5c.sh --skip-validate while the missing-file guard still fails before validation, so that branch can loop on the same defect
- **Proposed resolution**: Special-case the missing or empty composed-plan diagnostic before shared auto-repair and Override semantics: skip auto-repair for that diagnostic, make Fix-and-retry rerun Step 5c item 1 then normal design-step5c.sh, and do not offer or execute an Override path that skips validation without first composing the file




### FINDING_1: Missing harness for `--skip-validate` with empty or absent `composed-plan.md`
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan adds a hard invariant that `--skip-validate` cannot bypass a missing or empty `composed-plan.md` check, but test updates only cover the empty-file path without `--skip-validate` and the existing `--skip-validate` happy-path test. A mistaken reorder that evaluates `--skip-validate` before the composed-plan precondition could still pass tests while allowing Override-style retries to reach redaction and die on exit 5, recreating the session-killing abort this issue fixes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add a case after the current skip-validate happy-path test: empty or rm composed-plan.md, invoke with --skip-validate, expect exit 4, VALIDATE_STATUS=defects-found, and no redact/plan-block/rename/publish stubs
  - From Cursor-Pragmatic: Add one harness case: empty or absent composed-plan.md with --skip-validate must exit 4, emit VALIDATE_STATUS=defects-found, and skip redact/publish/rename stubs (mirror the expanded empty-file assertions).




### FINDING_2: Missing-composed-plan `--skip-validate` test needs an isolated tmpdir
- **Reviewer(s)**: Cursor-Pragmatic, Codex-Generic
- **Severity**: important
- **Concern**: The planned `--skip-validate` missing-`composed-plan.md` regression reuses `$D_SKIP` after the happy-path `--skip-validate` case (lines 483–509). That case already writes `composed-plan.redacted.md`, `.design-publish-result.env`, and full publish-side call-log entries. Removing or emptying `composed-plan.md` in the same directory leaves stale artifacts, so assertions such as `composed-plan.redacted.md` absent and publish/rename stubs not invoked can pass or fail for the wrong reason and will not catch ordering regressions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add a new tmpdir (for example `D_SKIP_NOP`) via `setup_design_tmp`, delete or truncate `composed-plan.md` there, call `reset_publish_stub_env` / `init_publish_logs`, then run `--skip-validate` and assert exit `4` on the clean tree only
  - From Codex-Generic: Use a fresh temp dir such as D_SKIP_MISSING and reset publish logs before invoking the missing-file --skip-validate case, or explicitly clear stale artifacts and logs first




### FINDING_1: Stale approval-gates.md Step 5c recovery routes missing composed-plan through --skip-validate
- **Reviewer(s)**: Cursor-Innovation, Codex-Generic
- **Severity**: important
- **Concern**: `approval-gates.md` still says all Step 5c validator recoveries (Override, Fix-and-retry, autofix-success) re-enter via `design-step5c.sh --skip-validate`. After `design-publish.sh` maps missing or empty `composed-plan.md` to exit 4, an orchestrator that follows this reference may skip Step 5c item 1 composition and retry only the wrapper, repeating the failure or exposing Override on a path that cannot succeed without composition first.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add a minimal approval-gates.md edit: missing or empty composed-plan.md uses compose-then-wrapper recovery with no Override; ordinary composed-plan validator defects keep the existing --skip-validate Override and autofix-success paths
  - From Codex-Generic: Update this reference to narrow --skip-validate to ordinary composed-plan validator defects only, and add the missing-composed-plan special case: compose Step 5c item 1 first, skip autofix, and offer Fix-and-retry or Cancel only.


### FINDING_2: SKILL.md Step 5c item 2 and _publish_rc=4 recovery still unconditional on --skip-validate
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: Step 5c item 2 and the `_publish_rc=4` paragraph document Fix-and-retry as re-invoking `design-step5c.sh` and Override as `--skip-validate` for any exit 4 defects. For missing-or-empty `composed-plan.md`, Fix-and-retry that only re-runs the wrapper repeats the original bug; Override still fails because the precondition runs before `--skip-validate`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: In item 2 and the _publish_rc=4 recovery text explicitly branch missing-or-empty composed-plan.md from ordinary validator defects require Fix-and-retry to re-run Step 5c item 1 before design-step5c.sh and omit Override for the missing-composed-plan diagnostic


### FINDING_3: Shared validator-failure handler must branch on missing/empty composed-plan file precondition
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: The shared **Plan command validator failure** path should detect skipped composition via a file precondition, not log substring alone. An empty `composed-plan.md` is still a regular file, so `plan auto-fix-commands` and the Step 5c autofix `ok` path can vendor-edit it and re-enter `design-step5c.sh --skip-validate`, publishing a plan that never went through Step 5c item 1 (`## Plan`, `## Acceptance`, `diff_lines`). If detection relies only on log text without pinning the exact diagnostic, implementers may match the wrong substring and diverge from `design-publish.sh` output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: In `### Plan command validator failure (shared)`, branch on `[[ ! -s "$DESIGN_TMPDIR/composed-plan.md" ]]` for `--site` `design Step 5c` before auto-repair: skip `design-step-validator-autofix.sh`, offer only Fix-and-retry (re-run Step 5c item 1) and Cancel, and keep Override only for ordinary defects where the composed plan already exists and is non-empty. Treat log text as diagnostic evidence only.
  - From Cursor-Requirements: In SKILL.md name the stable literal token composed-plan.md missing or empty matching the printf diagnostic written to validate-plan-commands.log and use that exact substring for the skip-auto-repair and no-Override branch



