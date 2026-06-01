### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/references/conflict-resolution.md:16,112
- **Concern**: Plan omits updating conflict-resolution Phase 4 resume. Scenario: Postbump step8b internal handoff sets RESUME_PHASE=force-push-gate but Phase 4 still tells the orchestrator to run ship-pr.sh --resume-phase ship-pr-rrr-phase14; resume hits die_usage (PHASE=bump) or CI rebase logic
- **Proposed resolution**: Add skills/implement/references/conflict-resolution.md to Files: for ship_pr_pre_push when state RESUME_PHASE is force-push-gate or ship-pr-rrr-phase14-postbump, Phase 4 exit 0 must re-invoke that token (or read RESUME_PHASE from ship-pr-state.sh), not ship-pr-rrr-phase14

### FINDING_2:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/ship-pr.sh:3377-3381; skills/implement/SKILL.md:1183-1184
- **Concern**: Plan assumes non-bump step8b handoff uses exit 5 + CALLER_KIND=ship_pr_pre_push; run_rebase_rebump actually calls exit_stall (exit 4, STALL_TRACKING=true). Scenario: After internal step8b hits non-bump-only conflicts, orchestrator follows Exit 4 → Step 16; conflict-resolution.md is never loaded despite RESUME_PHASE/CALLER_KIND/CONFLICT_FILES on stdout
- **Proposed resolution**: Align the plan with the live stall contract: either (a) step8b-family ship_pr_pre_push emits exit 5 with STALL_TRACKING=false and emit_kv CONFLICT_FILES, or (b) add an Exit 4 branch for CALLER_KIND=ship_pr_pre_push that runs Phase 1–4 before Step 16; update test-ship-pr expectations accordingly (they currently assert rc 4 for phase14)

### FINDING_3:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/ship-pr.sh:3377-3381
- **Concern**: Plan reuses run_rebase_rebump non-bump handoff but that path calls exit_stall after emit_kv not exit 5. Scenario: Orchestrator Exit 5 handler runs conflict-resolution only on rc 5; step8b internal non-bump escape that copies exit_stall leaves STALL_TRACKING true and skips Phase 1-4
- **Proposed resolution**: From run_step8b_rebase_rebump_internal emit_kv CONFLICT_FILES set RESUME_PHASE to postbump resume token and CALLER_KIND ship_pr_pre_push with STALL_TRACKING false then exit 5; do not call exit_stall for that branch

### FINDING_4:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/references/conflict-resolution.md:16,112
- **Concern**: Plan omits conflict-resolution.md while postbump non-bump conflicts use CALLER_KIND=ship_pr_pre_push and MANDATORY Phase 1–4 from that file. Scenario: Phase 4 exit 0 still hardcodes --resume-phase ship-pr-rrr-phase14 for ship_pr_pre_push; postbump internal step8b handoff would resume into CI run_rebase_rebump (die_usage or wrong phase) instead of force-push-gate
- **Proposed resolution**: Add conflict-resolution.md to Files to modify: branch ship_pr_pre_push Phase 4 exit 0 on RESUME_PHASE from ship-pr-state.sh (postbump token or force-push-gate) vs default ship-pr-rrr-phase14 for ci-initial|ci-merge; pair with SKILL.md Exit 5 bullet

### FINDING_5:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/ship-pr.sh:3377-3381
- **Concern**: Plan says exit 5 for step8b non-bump escape but does not require STALL_TRACKING=false distinct from run_rebase_rebump exit_stall pattern. Scenario: Copying the CI waterfall-exhausted block yields exit 4 with STALL_TRACKING=true; Step 8+ Exit 5 handler never runs and postbump Phase 1–4 is skipped
- **Proposed resolution**: Specify run_step8b_rebase_rebump_internal non-bump handoff: emit_kv CONFLICT_FILES then exit 5 with CALLER_KIND=ship_pr_pre_push RESUME_PHASE set to postbump resume token and STALL_TRACKING=false (mirror current step8b_rebase exit 5 at 1467-1469, not exit_stall)

### FINDING_6:
- **Reviewer(s)**: Cursor-dyn-resume-route
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:17
- **Concern**: Postbump Phase 1–4 resume token is explicitly deferred (dedicated ship-pr-rrr-phase14-postbump vs widening the PHASE guard). Scenario: Implementer must choose load-bearing dispatch semantics under scripts/ship-pr.sh:3772-3786 without design authority; wrong choice either die_usage on bump-phase resume or re-enters CI tail
- **Proposed resolution**: Commit in plan: prefer a dedicated resume token that resumes force-push-gate (maps to scripts/ship-pr.sh:3766) and leaves the ci-initial|ci-merge guard at 3774-3776 untouched; document why widening ship-pr-rrr-phase14 is rejected
