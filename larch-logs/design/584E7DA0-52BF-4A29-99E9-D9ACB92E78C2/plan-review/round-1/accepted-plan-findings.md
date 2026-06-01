### FINDING_1: Postbump resume token and Phase 4 dispatch not specified in plan
- **Reviewer(s)**: Cursor-Arch, Cursor-Requirements, Cursor-dyn-resume-route
- **Severity**: important
- **Concern**: The plan does not update `conflict-resolution.md` or commit resume-token semantics for postbump step8b internal handoff. Today `ship_pr_pre_push` Phase 4 exit 0 always re-invokes `--resume-phase ship-pr-rrr-phase14` (see lines 16 and 112), while postbump handoff can set `RESUME_PHASE` to `force-push-gate` or a deferred postbump token. Resuming the wrong phase hits `die_usage` when `PHASE=bump`, or re-enters CI `run_rebase_rebump` instead of the force-push gate. The plan also defers choosing between a dedicated `ship-pr-rrr-phase14-postbump` token and widening the `ship-pr-rrr-phase14` guard at `scripts/ship-pr.sh:3772-3786`, leaving load-bearing dispatch to the implementer without design authority.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add skills/implement/references/conflict-resolution.md to Files: for ship_pr_pre_push when state RESUME_PHASE is force-push-gate or ship-pr-rrr-phase14-postbump, Phase 4 exit 0 must re-invoke that token (or read RESUME_PHASE from ship-pr-state.sh), not ship-pr-rrr-phase14
  - From Cursor-Requirements: Add conflict-resolution.md to Files to modify: branch ship_pr_pre_push Phase 4 exit 0 on RESUME_PHASE from ship-pr-state.sh (postbump token or force-push-gate) vs default ship-pr-rrr-phase14 for ci-initial|ci-merge; pair with SKILL.md Exit 5 bullet
  - From Cursor-dyn-resume-route: Commit in plan: prefer a dedicated resume token that resumes force-push-gate (maps to scripts/ship-pr.sh:3766) and leaves the ci-initial|ci-merge guard at 3774-3776 untouched; document why widening ship-pr-rrr-phase14 is rejected


### FINDING_2: step8b non-bump handoff uses exit_stall (4), not exit 5 — orchestrator skips Phase 1–4
- **Reviewer(s)**: Cursor-Edge, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: The plan assumes postbump step8b non-bump conflicts hand off via exit 5 with `CALLER_KIND=ship_pr_pre_push` so the orchestrator loads `conflict-resolution.md` and runs Phase 1–4. Live code at `scripts/ship-pr.sh:3377-3381` (and the `run_rebase_rebump` / `run_step8b_rebase_rebump_internal` path reviewers cite) emits `RESUME_PHASE` / `CALLER_KIND` / `CONFLICT_FILES` then calls `exit_stall` (exit 4, `STALL_TRACKING=true`). The orchestrator’s Exit 5 handler runs conflict-resolution; Exit 4 routes to Step 16, so Phase 1–4 is never loaded despite keys on stdout. Tests currently assert rc 4 for phase14 on this path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Align the plan with the live stall contract: either (a) step8b-family ship_pr_pre_push emits exit 5 with STALL_TRACKING=false and emit_kv CONFLICT_FILES, or (b) add an Exit 4 branch for CALLER_KIND=ship_pr_pre_push that runs Phase 1–4 before Step 16; update test-ship-pr expectations accordingly (they currently assert rc 4 for phase14)
  - From Cursor-Pragmatic: From run_step8b_rebase_rebump_internal emit_kv CONFLICT_FILES set RESUME_PHASE to postbump resume token and CALLER_KIND ship_pr_pre_push with STALL_TRACKING false then exit 5; do not call exit_stall for that branch
  - From Cursor-Requirements: Specify run_step8b_rebase_rebump_internal non-bump handoff: emit_kv CONFLICT_FILES then exit 5 with CALLER_KIND=ship_pr_pre_push RESUME_PHASE set to postbump resume token and STALL_TRACKING=false (mirror current step8b_rebase exit 5 at 1467-1469, not exit_stall)

