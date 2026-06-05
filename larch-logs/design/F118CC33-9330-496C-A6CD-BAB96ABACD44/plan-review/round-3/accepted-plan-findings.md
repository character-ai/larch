### FINDING_1: Implement timing-report callers can inherit design workflow env
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Concern**: Implement-owned timing-report invocations may still read ambient `LARCH_TIMING_SKILL=design` / `DESIGN_TMPDIR` state and emit design SIMPLE/HARD workflow data, undermining the intended implement workflow removal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add minimal plan steps to prefix implement timing-report invocations with LARCH_TIMING_SKILL=implement, and cover a polluted-env caller harness case; optionally clear DESIGN_TMPDIR for those calls


### FINDING_2: Report-token issue trimming is not fully skill-aware
- **Reviewer(s)**: Codex-Requirements, Cursor-dyn-operator-surface
- **Severity**: important
- **Concern**: The plan updates omitted-section wording for implement reports but does not fully cover aggregate omission tests or the CLI call path, so trimmed implement issues may still mention the old workflow aggregate label while design behavior can regress unnoticed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add a focused test_report_tokens_issue.py case that forces aggregate omission for implement and design; if the implementation gates on skill, thread skill through the issue assembly/posting call path as part of that same minimal change
  - From Cursor-dyn-operator-surface: Add python/report_tokens_cli.py to the plan and pass skill into post_issue/assemble_issue_body/_section_label


### FINDING_3: Implement scan tests do not prove legacy timing-report artifacts are ignored
- **Reviewer(s)**: Cursor-dyn-legacy-artifacts
- **Severity**: important
- **Concern**: Planned scan coverage for `workflow == ""` may miss committed implement-log shapes where `timing-report.json` contains `workflow_path`, allowing regressions that re-split implement report-token output by legacy HARD/SIMPLE.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-legacy-artifacts: Add test_scan_implement_ignores_legacy_timing_report_json: implement run dir with only timing-report.json {"workflow_path":"HARD"}; assert record.workflow=="" and no stderr from _workflow_from on that path; implement early-return must precede any path.is_file loop


### FINDING_4: Final-report tests delete rather than prove ignoring legacy workflow flags
- **Reviewer(s)**: Codex-dyn-legacy-artifacts
- **Severity**: important
- **Concern**: Removing legacy fixture values does not demonstrate that stale `WORKFLOW_PATH` or `POST_PLAN_WORKFLOW_PATH` artifacts are ignored, so a surviving read/pass-through could still leak a Path bullet.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-legacy-artifacts: Keep one test-write-final-report fixture with legacy WORKFLOW_PATH and POST_PLAN_WORKFLOW_PATH values and assert the final summary contains no - **Path** line and no leaked SIMPLE/HARD path value


### FINDING_5: Step 5 operator docs may retain retired hard-panel wording
- **Reviewer(s)**: Codex-dyn-operator-surface
- **Severity**: latent
- **Concern**: The planned Step 5 doc edit may remove only the `WORKFLOW_PATH`-as-HARD detail while leaving adjacent wording that still describes a retired unified hard review panel.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-operator-surface: While editing these two planned files, replace the remaining unified hard panel clause with neutral wording such as the default Step 5 review panel is selected inside review-and-fix.sh


### FINDING_6: PR-summary script contract still references SIMPLE-path implement runs
- **Reviewer(s)**: Codex-dyn-operator-surface
- **Severity**: latent
- **Concern**: The plan misses operator-facing wording in `compose-pr-summary` that still advertises a SIMPLE-path `/implement` mode after implement workflow classification is removed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-operator-surface: Change the sentence to describe the actual caller without tier wording, for example replacing the static PR body placeholder during /implement PR prep

