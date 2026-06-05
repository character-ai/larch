### FINDING_1:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/scripts/step-7a.sh:150-151; scripts/refresh-run-logs.sh:76-79; scripts/implement-finalize.sh:392-394
- **Concern**: Plan gates timing-report workflow fallback on LARCH_TIMING_SKILL but leaves implement-owned timing-report callers exposed to ambient environment. Scenario: If LARCH_TIMING_SKILL=design and DESIGN_TMPDIR leak from a prior design session, Step 7a or pre-push refresh can still write implement timing-report JSON with design SIMPLE/HARD instead of unknown, defeating the proposed implement workflow removal
- **Proposed resolution**: Add minimal plan steps to prefix implement timing-report invocations with LARCH_TIMING_SKILL=implement, and cover a polluted-env caller harness case; optionally clear DESIGN_TMPDIR for those calls

### FINDING_2:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/report_tokens_issue.py:20-23; python/test_report_tokens_issue.py:58-67
- **Concern**: Plan changes aggregate omitted-section wording for implement but does not add issue-trimming coverage for that new acceptance. Scenario: An oversized implement report can still omit the aggregate section with the old “Aggregate cost by workflow” label, or design wording can regress, while existing tests pass because they only trim the trends section
- **Proposed resolution**: Add a focused test_report_tokens_issue.py case that forces aggregate omission for implement and design; if the implementation gates on skill, thread skill through the issue assembly/posting call path as part of that same minimal change

### FINDING_3:
- **Reviewer(s)**: Cursor-dyn-legacy-artifacts
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/report_tokens_scan.py:111-123
- **Concern**: Plan updates implement scan tests for workflow=="" but does not require a fixture shaped like committed implement logs (timing-report.json with workflow_path HARD, no run-params.json). Scenario: Today _workflow reads timing-report.json first and returns HARD for those dirs; a regression that reopens artifacts would silently re-split report-tokens implement output by legacy HARD/SIMPLE
- **Proposed resolution**: Add test_scan_implement_ignores_legacy_timing_report_json: implement run dir with only timing-report.json {"workflow_path":"HARD"}; assert record.workflow=="" and no stderr from _workflow_from on that path; implement early-return must precede any path.is_file loop

### FINDING_4:
- **Reviewer(s)**: Codex-dyn-legacy-artifacts
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/write-final-report.sh:116-118,434-440,458-465
- **Concern**: Legacy run-flags and session-env workflow readers are removed, but the proposed tests delete WORKFLOW_PATH fixtures instead of proving old artifacts are ignored. Scenario: A historical tmpdir containing WORKFLOW_PATH=HARD or POST_PLAN_WORKFLOW_PATH=SIMPLE could still leak a Path bullet if one read/pass-through survives the edit
- **Proposed resolution**: Keep one test-write-final-report fixture with legacy WORKFLOW_PATH and POST_PLAN_WORKFLOW_PATH values and assert the final summary contains no - **Path** line and no leaked SIMPLE/HARD path value

### FINDING_5:
- **Reviewer(s)**: Cursor-dyn-operator-surface
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/report_tokens_cli.py:114-118
- **Concern**: Plan makes report_tokens_issue.py skill-aware for omitted-section labels but omits the CLI caller. Scenario: post_issue/assemble_issue_body still have no skill parameter so trimmed implement issues can keep listing Aggregate cost by workflow in the Omitted sections notice
- **Proposed resolution**: Add python/report_tokens_cli.py to the plan and pass skill into post_issue/assemble_issue_body/_section_label

### FINDING_6:
- **Reviewer(s)**: Codex-dyn-operator-surface
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: scripts/run-step5-review.md:28 and scripts/test-run-step5-review.md:10
- **Concern**: Planned Step 5 doc reword only drops WORKFLOW_PATH treated as HARD and can leave the retired unified hard panel wording in the same paragraph. Scenario: After the PR, operator-facing Step 5 contracts may still describe a hard panel even though implement workflow classification is being removed
- **Proposed resolution**: While editing these two planned files, replace the remaining unified hard panel clause with neutral wording such as the default Step 5 review panel is selected inside review-and-fix.sh

### FINDING_7:
- **Reviewer(s)**: Codex-dyn-operator-surface
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: scripts/compose-pr-summary.md:3-5
- **Concern**: The plan misses a script contract that still says compose-pr-summary replaces the static placeholder on SIMPLE-path /implement runs. Scenario: After the PR, this operator-facing contract still advertises an implement SIMPLE path that no longer exists
- **Proposed resolution**: Change the sentence to describe the actual caller without tier wording, for example replacing the static PR body placeholder during /implement PR prep
