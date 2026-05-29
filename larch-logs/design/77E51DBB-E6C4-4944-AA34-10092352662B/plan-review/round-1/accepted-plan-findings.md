### FINDING_1: Gate B docs retain legacy diff hard-trigger semantics
- **Reviewer(s)**: Cursor-Arch, Cursor-Edge, Codex-Edge, Codex-Pragmatic, Codex-dyn-doc-sync
- **Severity**: important
- **Concern**: `skills/design/references/approval-gates.md` still describes the old `DIFF_LINES > 1500` hard gate, so Gate B guidance can contradict the new `diff_added` / deletion / `mechanical_churn` behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add skills/design/references/approval-gates.md to the plan (mirror the flags.md hard-trigger bullets: diff_added > 2000 when present, else diff_lines > 1500, deletions exempt, mechanical_churn soft advisory) and extend the testing-strategy grep beyond docs/ and README.md to skills/design/references/
  - From Cursor-Edge, Codex-Edge: Update this Gate B summary in the plan to match the new Step 2b.5 contract: plan body > 800; diff_added > 2000 when present else diff_lines > 1500; deletions exempt; mechanical_churn advisory only
  - From Codex-Pragmatic: Add approval-gates.md to the plan and replace the parenthetical with the new Step 2b.5 semantics or a direct pointer to SKILL.md/check-plan-size.sh
  - From Codex-dyn-doc-sync: Add skills/design/references/approval-gates.md to Files to modify/create or broaden the testing/doc-sync step to grep/update skills/**/*.md as well as docs/ and README.md


### FINDING_2: Plan revision paths can drop optional size trailers
- **Reviewer(s)**: Codex-Arch, Cursor-Innovation, Codex-Innovation, Codex-Requirements
- **Severity**: important
- **Concern**: Gate B and plan-review revision flows can rewrite `plan.txt` while preserving only `diff_lines`, causing later size checks to lose `diff_added`, `diff_deleted`, or `mechanical_churn` and fall back to the legacy hard gate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Update the plan to preserve or carry forward diff_added, diff_deleted, and mechanical_churn above the final diff_lines line in Gate B apply-all and revise-plan-with-waterfall, with a focused regression for one revision path.
  - From Cursor-Innovation, Codex-Innovation: Update the revision prompts and Gate B prose to preserve or recompute diff_added, diff_deleted, and mechanical_churn above final diff_lines when present; add one regression that a mechanical_churn plan survives plan-review or Gate B revision without becoming plan-size-trigger
  - From Codex-Requirements: Add the minimum contract edits for Gate B and revise-plan-with-waterfall to preserve existing diff_added, diff_deleted, and mechanical_churn trailers across plan rewrites, update the stale Gate B hard-trigger prose, and add one regression or spot-check where a revised mechanical_churn plan does not return plan-size-trigger


### FINDING_3: Optional trailer parsing can be spoofed by plan body text
- **Reviewer(s)**: Cursor-Edge, Codex-Edge
- **Severity**: important
- **Concern**: `check-plan-size.sh` scans the full file for optional trailer keys, so ordinary prose or code blocks containing lines like `mechanical_churn: true` or `diff_added: 0` can unintentionally change gate behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge, Codex-Edge: Restrict optional trailer parsing to a final contiguous metadata block immediately above the required final diff_lines line, then update the tests/docs to pin that narrower contract


### FINDING_4: Soft advisory text can contradict a remaining hard gate
- **Reviewer(s)**: Cursor-dyn-combined-gate-flow, Codex-dyn-combined-gate-flow
- **Severity**: important
- **Concern**: Step 2b.5 can print a “proceeding” advisory when the diff gate is downgraded even though `HARD_TRIGGER_FIRED` remains true because the plan-body line gate still requires Split/Cancel.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-combined-gate-flow, Codex-dyn-combined-gate-flow: Keep the minimum change: make the advisory text conditional. Use "proceeding" only when HARD_TRIGGER_FIRED=false; when HARD_TRIGGER_FIRED=true, print "diff gate downgraded; plan-body gate still requires Split/Cancel" or include the advisory inside the hard section.


