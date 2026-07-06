### OOS_1: Fix B targets "all loaded contract surfaces" but the plan only calls out Step 3 in skills/design/SKILL.md while Step 5c keeps inline "empty output yields silently" / probe-only wording
- **Description**: Fix B targets "all loaded contract surfaces" but the plan only calls out Step 3 in skills/design/SKILL.md while Step 5c keeps inline "empty output yields silently" / probe-only wording. Scenario: Long Step 5c publish waits can hit the same premature-notification + empty tasks/*.output pattern; hook allow alone does not tell the Step 5c orchestrator to Read for emptiness before silent yield
- **Reviewer**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: skills/design/SKILL.md:622
- **Phase**: design




Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

### OOS_2: SECURITY.md still documents blanket Read denial for task outputs during live bg waits (ledger OOS_2)
- **Description**: SECURITY.md still documents blanket Read denial for task outputs during live bg waits (ledger OOS_2). Scenario: Operators reading SECURITY.md get the pre-fix deny story and may misdiagnose allowed classification Reads as a policy violation
- **Reviewer**: Cursor-Arch
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: SECURITY.md:224
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### OOS_4: SECURITY.md still documents that the bg-poll hook denies task-output reads during live waits. After Fix A, Read of tasks/*.output is allowed during live same-clone waits for emptiness classification.
- **Description**: SECURITY.md still documents that the bg-poll hook denies task-output reads during live waits. After Fix A, Read of tasks/*.output is allowed during live same-clone waits for emptiness classification.. Scenario: Track a follow-up issue to update SECURITY.md hook invariants so security docs match hook-bg-poll-guard.md.
- **Reviewer**: Cursor-Requirements
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: SECURITY.md:224
- **Phase**: design

Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

