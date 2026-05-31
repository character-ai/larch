### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:168-170
- **Concern**: LOAD_OK=false ERROR breadcrumb is nested under the cancel-title-filter ROUTE bullet instead of a global pre-branch step. Scenario: After pause-load failure the orchestrator may skip re-emitting ERROR on proceed/clarify/already-planned paths, diverging from today's sub-step 2.5-bis and the Edge cases section
- **Proposed resolution**: Move ERROR re-emit to the same level as the BRAINSTORM_PREFIX pre-branch bullet (before any ROUTE branch); keep cancel-title-filter bullet exit-only

### FINDING_2:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:164-170
- **Concern**: ERROR re-emit scoped only under cancel-title-filter bullet. Scenario: Pause-load LOAD_OK=false fallthrough to ROUTE=clarify or already-planned skips ERROR breadcrumb; regresses current Step 0b prose that warns on any fresh-run path after failed pause load
- **Proposed resolution**: In SKILL.md: immediately after reading .design-route-result.env, if ERROR is non-empty print it once as a warning breadcrumb before the ROUTE branch (not only on cancel-title-filter)

### FINDING_3:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:193-198
- **Concern**: FINDING_13 harness checks env refresh before write-run-params but not before rename. Scenario: Reorder to rename → env → write-run-params would still pass harness while breaking Decision 1 ISSUE_NUMBER binding before pause-save
- **Proposed resolution**: Add line-order assert in test-design-structure.sh: write-design-current-env.sh precedes tracking-issue-write.sh rename in design-init-runparams.sh

### FINDING_4:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:156-183
- **Concern**: No orchestrator contract for design-route.sh non-zero exits. Scenario: Exit 2 (argv/body-file) or exit 1 (set -e after phase_driver_write_result_env failure) can leave ROUTE unset and fall through gates
- **Proposed resolution**: Specify SKILL.md handling: on design-route exit 2 print config error and exit 1; treat unexpected non-zero like run-step3-review exit 2 (do not branch on empty ROUTE)

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-route.sh:86-88
- **Concern**: Verdict step 4 does not define how to detect a larch:plan block in issue-body.txt. Scenario: Implementer may use a loose substring grep and mis-route (false already-planned) or miss valid blocks; diverges from plan-block-read.sh marker rules used elsewhere
- **Proposed resolution**: Pin detection to the same start/end marker regexes as scripts/plan-block-read.sh (lines 20-21) on the body file; treat only well-formed single start+end pairs as present (no extra gh fetch)
