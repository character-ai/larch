### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/design/references/approval-gates.md:161
- **Concern**: Gate B hard-trigger prose still says PLAN_LINES > 800 or DIFF_LINES > 1500 only. Scenario: After the change, a plan with diff_added: 2100 and diff_lines: 400 hard-triggers via diff-added, but Gate B readers following approval-gates.md will believe it is under the diff gate; conversely diff_lines: 2000 with diff_added: 500 will not hard-trigger but the doc still implies DIFF_LINES > 1500 is sufficient
- **Proposed resolution**: Add skills/design/references/approval-gates.md to the plan (mirror the flags.md hard-trigger bullets: diff_added > 2000 when present, else diff_lines > 1500, deletions exempt, mechanical_churn soft advisory) and extend the testing-strategy grep beyond docs/ and README.md to skills/design/references/

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/references/approval-gates.md:131-157, skills/design/scripts/revise-plan-with-waterfall.sh:126-134, skills/design/scripts/plan-review-loop.sh:638-645
- **Concern**: Plan revision paths can drop the new optional trailers before re-running the size gate. Scenario: A mechanical-churn plan passes the initial Step 2b.5 check, then Gate B or the multi-round loop rewrites plan.txt while preserving only diff_lines. The next check falls back to legacy diff_lines > 1500 and forces Split/Cancel, losing the proposed advisory behavior.
- **Proposed resolution**: Update the plan to preserve or carry forward diff_added, diff_deleted, and mechanical_churn above the final diff_lines line in Gate B apply-all and revise-plan-with-waterfall, with a focused regression for one revision path.

### FINDING_3:
- **Reviewer(s)**: Cursor-Edge, Codex-Edge
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/references/approval-gates.md:159-161
- **Concern**: Gate B reference keeps the old DIFF_LINES hard-threshold contract. Scenario: Gate B can still tell the executor that DIFF_LINES > 1500 is hard even when diff_added is present, deletions are exempt, or mechanical_churn downgrades the diff gate
- **Proposed resolution**: Update this Gate B summary in the plan to match the new Step 2b.5 contract: plan body > 800; diff_added > 2000 when present else diff_lines > 1500; deletions exempt; mechanical_churn advisory only

### FINDING_4:
- **Reviewer(s)**: Cursor-Edge, Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/check-plan-size.sh:67-96
- **Concern**: Full-file optional-trailer scan lets body content masquerade as metadata. Scenario: A plan that includes a code block or prose line exactly mechanical_churn: true or diff_added: 0 can silently suppress or change the hard gate without the designer appending an intentional trailer
- **Proposed resolution**: Restrict optional trailer parsing to a final contiguous metadata block immediately above the required final diff_lines line, then update the tests/docs to pin that narrower contract

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation, Codex-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/revise-plan-with-waterfall.sh:126-134; skills/design/references/approval-gates.md:133-161
- **Concern**: New optional size trailers are not preserved by plan-revision paths. Scenario: After Step 2b emits diff_added or mechanical_churn for a large mechanical-deletion plan, Step 3 auto-revision or Gate B apply rewrites plan.txt under prompts that require only final diff_lines; the next Step 2b.5 check falls back to legacy diff_lines and can fire the Split/Cancel hard gate the new contract was meant to avoid
- **Proposed resolution**: Update the revision prompts and Gate B prose to preserve or recompute diff_added, diff_deleted, and mechanical_churn above final diff_lines when present; add one regression that a mechanical_churn plan survives plan-review or Gate B revision without becoming plan-size-trigger

### FINDING_6:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/references/approval-gates.md:159-161
- **Concern**: Gate B reference keeps the legacy DIFF_LINES hard-trigger summary. Scenario: After Gate B post-apply, the executor reads approval-gates.md and may route a deletion-heavy or mechanical-churn plan to Split/Cancel despite check-plan-size.sh downgrading the diff gate
- **Proposed resolution**: Add approval-gates.md to the plan and replace the parenthetical with the new Step 2b.5 semantics or a direct pointer to SKILL.md/check-plan-size.sh

### FINDING_7:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/references/approval-gates.md:133-161; skills/design/scripts/revise-plan-with-waterfall.sh:126-134; skills/design/scripts/plan-review-loop.sh:638-645
- **Concern**: Plan omits plan-revision surfaces that rewrite plan.txt before re-running the size gate. Scenario: For a deletion-heavy or mechanical plan, Step 2b.5 can initially honor diff_added or mechanical_churn, but the review loop or Gate B rewrite only requires preserving diff_lines and may drop the new optional trailers; the immediate check-plan-size call then falls back to DIFF_LINES > 1500 and raises the old Split/Cancel hard gate
- **Proposed resolution**: Add the minimum contract edits for Gate B and revise-plan-with-waterfall to preserve existing diff_added, diff_deleted, and mechanical_churn trailers across plan rewrites, update the stale Gate B hard-trigger prose, and add one regression or spot-check where a revised mechanical_churn plan does not return plan-size-trigger

### FINDING_8:
- **Reviewer(s)**: Cursor-dyn-combined-gate-flow, Codex-dyn-combined-gate-flow
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:44, <TMPDIR>/plan.txt:59, <TMPDIR>/plan.txt:77
- **Concern**: Step 2b.5 prints a "proceeding" soft advisory before the hard branch even when HARD_TRIGGER_FIRED remains true from plan-body lines. Scenario: The proposed plan_lines 801 plus mechanical_churn true case emits SOFT_ADVISORY=true and then immediately shows the non-continue Split/Cancel hard prompt, giving contradictory operator signals
- **Proposed resolution**: Keep the minimum change: make the advisory text conditional. Use "proceeding" only when HARD_TRIGGER_FIRED=false; when HARD_TRIGGER_FIRED=true, print "diff gate downgraded; plan-body gate still requires Split/Cancel" or include the advisory inside the hard section.

### FINDING_9:
- **Reviewer(s)**: Cursor-dyn-doc-sync
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:38
- **Concern**: `check-plan-size.md` update says "Keep the existing 'Edit in sync' list" while only expanding surrounding prose. Scenario: Implementers can change optional trailers (`diff_added` / `diff_deleted` / `mechanical_churn`) or output keys (`DIFF_ADDED` / `DIFF_DELETED` / `MECHANICAL_CHURN` / `SOFT_ADVISORY`) without the sibling contract reminding them which surfaces must move together
- **Proposed resolution**: Replace "Keep the existing" with an explicit Edit-in-sync expansion: name the three optional input trailers and four machine-output keys, and add `skills/design/references/approval-gates.md` (Gate B Step 2b.5 summary at :161) to the file list

### FINDING_10:
- **Reviewer(s)**: Codex-dyn-doc-sync
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:87-92; skills/design/references/approval-gates.md:159-161
- **Concern**: Plan only commits to grepping docs/ and README.md for stale threshold prose, but a stale Step 2b.5 contract lives outside that scope in skills/design/references/approval-gates.md. Scenario: After this PR, Gate B docs would still say hard trigger is PLAN_LINES > 800 or DIFF_LINES > 1500, omitting diff_added > 2000 and mechanical_churn downgrade
- **Proposed resolution**: Add skills/design/references/approval-gates.md to Files to modify/create or broaden the testing/doc-sync step to grep/update skills/**/*.md as well as docs/ and README.md

### FINDING_11:
- **Reviewer(s)**: Codex-dyn-doc-sync
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: plan.txt:34-38; skills/design/scripts/check-plan-size.md:41-43
- **Concern**: The plan says to keep the existing Edit in sync list, so it does not explicitly expand that cross-reference for the three optional input trailers and four new emitted keys. Scenario: Future contract edits can update threshold prose while missing the new trailer/output-key consumers the doc-sync list is supposed to pin
- **Proposed resolution**: Revise the check-plan-size.md plan item so Edit in sync explicitly mentions optional trailer grammar and emitted-key contract changes, including DIFF_ADDED, DIFF_DELETED, MECHANICAL_CHURN, and SOFT_ADVISORY
