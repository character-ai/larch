### FINDING_1:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:458-480
- **Concern**: The plan adds a `skip_approve_requested` jq OR-merge arm but does not explicitly require updating the outer OR-merge entry `if` that gates that block (today only `partition_requested`, `brainstorm_requested`, or `approve_requested`).. Scenario: Edge cases document argv-only `--skip-approve` on `resume@*` / `already-planned` (plan.txt:149). If the outer predicate is left unchanged, re-entry with only `--skip-approve` skips the merge entirely; gates re-reading `run-params.json` keep `skip_approve_requested=false` and still fire outline/Gate C `AskUserQuestion` despite argv.
- **Proposed resolution**: State explicitly that the outer `if [[ ... ]]` must gain `|| "$skip_approve_requested" == true` (and the `SKIP_APPROVE_REQUESTED` analogue in `design-init-runparams.sh` / `test-step0b-router-flag-recovery.sh`) in every merge site, not only the jq filter; add a structural pin for the SKILL.md route-fence outer guard (today only the `$merge_a` arm is pinned in `test-step0b-router-flag-recovery.sh` case 12).

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1407-1420
- **Concern**: Gate C Step 4b still tells the orchestrator to Execute the Gate C body (including Prompt) and ends with Loop continues until the user picks Approve before the skip branch is unambiguous. Scenario: Under --skip-approve an implementer can still fire Gate C AskUserQuestion or treat Gate C as an interactive loop because approval-gates.md Prompt and SKILL.md line 1420 loop prose stay unconditional relative to the new emit-fence skip read
- **Proposed resolution**: Gate the entire post-emit interactive block on skip_approve_requested=false: after the emit fence prints SKIP_APPROVE_REQUESTED= auto-approve with breadcrumb and jump to Step 5; wrap approval-gates.md Prompt plus SKILL.md cap-aware option text and loop-until-Approve sentence in the same guard; add a structural pin that skip=true paths omit AskUserQuestion under Step 4b

### FINDING_3:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/SKILL.md:1411-1420
- **Concern**: Gate C --skip-approve bypasses See full plan / Other escalation after summary-mode preview. Scenario: When plan.txt line count exceeds LARCH_DESIGN_PLAN_SUMMARY_THRESHOLD the gatec preview is title+outline only; auto-approve proceeds to Step 5/publish without any interactive path to cat the full plan in chat (manual Gate C still offers See full plan / Other)
- **Proposed resolution**: Before auto-approve when skip_approve_requested=true and summary mode fired, cat plan.txt under ## Final Design Plan (or fail closed) and document the behavior in flags.md + SECURITY.md

### FINDING_4:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: security
- **Location**: skills/design/SKILL.md:1411-1420
- **Concern**: Gate C reads skip_approve_requested in the same fence that emits untrusted plan text. Scenario: A plan body can contain spoofed SKIP_APPROVE_REQUESTED=true text or binding instructions; if the orchestrator binds the spoofed line, Gate C can skip the final AskUserQuestion even without --skip-approve
- **Proposed resolution**: Keep the preview unchanged, then run a separate read-only fence that emits only the trusted SKIP_APPROVE_REQUESTED=<bool> line and branch only on that value.

### FINDING_5:
- **Reviewer(s)**: Cursor-dyn-token-sweep
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-init-runparams.md:18
- **Concern**: Plan UPDATED section documents skip_approve forwarding but omits renaming the public-flag prose Public `--approve` to `--per-round-approval`. Scenario: Post-change token grep `(?<![A-Za-z0-9_])--approve(?!-requested)` still hits this contract row; operators reading design-init-runparams.md see the retired public flag
- **Proposed resolution**: In the design-init-runparams.md UPDATED block add an explicit bullet: rename the argv-table note on line 18 from Public `--approve` to Public `--per-round-approval` (keep `--approve-requested` internal CLI name unchanged)

### FINDING_6:
- **Reviewer(s)**: Cursor-dyn-gate-wire
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/approval-gates.md:172-193
- **Concern**: Plan adds Gate C auto-approve prose but does not require qualifying Presentation→Prompt handoff or wrapping the full Prompt subtree. Scenario: `### Presentation` still says execution unconditionally "continues to the Prompt" (line 174) and the Large-plan summary paragraph documents See-full-plan / Other re-prompt loops as if always reachable; only a sibling auto-approve bullet is added. An implementer following Presentation→Prompt order can still fire the initial `AskUserQuestion` and cap-aware re-prompts (Discuss further, Re-run review panel, See full plan minus-self, Other unchanged) under `--skip-approve`, defeating the flag.
- **Proposed resolution**: Insert `### Auto-approve (--skip-approve)` immediately after Presentation and before Prompt; change Presentation handoff to "continue to auto-approve branch or Prompt when `skip_approve_requested=false`"; prefix the entire `### Prompt` block (including all re-fire / Other / cap-aware text) with that guard; extend `### Loop exit` to cover programmatic auto-approve → Step 5.
