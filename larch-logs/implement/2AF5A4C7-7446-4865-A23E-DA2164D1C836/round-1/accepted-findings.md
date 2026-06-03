### FINDING_1: code-quality: scripts/test-implement-rebase-macro.sh:170-190
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Harness sections (H) and (I) still require step8b_rebase and rebase-push.sh --no-push prose inside the retirement stub rebase-rebump-subprocedure.md make test-harnesses-13 fails on a clean tree after Phase 1 stubbing Update (H) to pin the live call site outside the stub; restrict (I) to conflict-resolution.md for still-valid tokens only
- **Suggested revision**: Address the concern above.


### FINDING_13: risk-integration: scripts/ship-pr.sh:1105-1110 + skills/implement/SKILL.md:1036
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Branch removes ship-pr.sh exit 5 (main had one postbump path); SKILL.md still documents Exit 5 orchestrator conflict-resolution. Step 8b rebase conflicts stall via exit 4 / exit_stall 8b instead of the documented Exit 5 + conflict-resolution.md handoff; orchestrator following SKILL may never run Phase 1-4 conflict resolution. Align SKILL exit matrix with actual exits; or restore exit 5 + CONFLICT_FILES where documented; add grep pin that ship-pr exit codes match SKILL.
- **Suggested revision**: Address the concern above.


### FINDING_28: risk-integration: skills/implement/SKILL.md:1035-1036
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Step 8+ Exit 5 handler is dead while ship_pr_pre_push conflict handoff now exits 4 via exit_stall. After run_rebase_rebump sets RESUME_PHASE=ship-pr-rrr-phase14 and emits CONFLICT_FILES, orchestrator follows Exit 4 to Step 16 stall instead of conflict-resolution Phase 1-4; CI-fix rebase conflicts stall without resume. Restore exit 5 for this handoff only, or teach Exit 4 to branch on RESUME_PHASE/CALLER_KIND and run conflict-resolution before Step 16; sync ship-pr.md.
- **Suggested revision**: Address the concern above.


### FINDING_29: correctness: scripts/test-implement-rebase-macro.sh:170-190
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] test-implement-rebase-macro still requires retired rebase-rebump-subprocedure.md prose; test fails (H count=0, I grep miss). make lint / test-harnesses-13 fails on this branch despite acceptance criteria. Rewrite sections H and I for Phase 1 stub and current call sites (implement-finalize/ship-pr/conflict-resolution.md).
- **Suggested revision**: Address the concern above.


### FINDING_37: architecture: skills/implement/scripts/hook-stop-fail-close.md
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Sibling doc still documents removed .bump-version-armed Stop-hook block. Operators trust md over sh and attempt obsolete Step-8 recovery. Strike bump section; document Phase 1 retirement.
- **Suggested revision**: Address the concern above.


### FINDING_38: correctness: .claude/skills/bump-version/SKILL.md:36-37
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] PATCH policy still says every PR must bump. Manual/release bump skill contradicts Phase 1 /implement path. Reword to release/operator-initiated bump policy.
- **Suggested revision**: Address the concern above.


### FINDING_7: correctness: skills/implement/SKILL.md:1036
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Exit 5 requires reading conflict-resolution.md which still describes removed bump flows. Same as above on any ship_pr_pre_push exit 5 during CI-fix rebase. Update conflict-resolution.md; optional explicit Phase 1 pointer in SKILL Exit 5 bullet.
- **Suggested revision**: Address the concern above.


### FINDING_8: correctness: scripts/test-implement-rebase-macro.sh:170-190
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Harness still pins retired stub/sub-procedure strings; test exits 1 on this tree. make lint / relevant-checks fails invariant (H) despite plan claiming green harnesses. Update (H)/(I) pins for Phase 1 retirement stub and revised conflict-resolution.md.
- **Suggested revision**: Address the concern above.


