### FINDING_1: risk-integration: scripts/test-implement-structure.sh:342-363
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Structural pins still require plan-materialization token/timing ledger marks and comment pairs in skills/implement/SKILL.md after those calls moved to scripts/implement-bootstrap.sh. make test-implement-structure fails four grep checks on every CI run while test-implement-bootstrap passes, blocking merge. Retarget pins to scripts/implement-bootstrap.sh for plan marks; keep tracking marks in SKILL.md; remove obsolete SKILL comment-pair requirements for plan materialization.
- **Suggested revision**: Address the concern above.

### FINDING_2: risk-integration: skills/implement/SKILL.md:463-467
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Dirty-tree recovery orchestrator flow (sentinel, AskUserQuestion, clean re-check, --resume-plan-tail) has no harness beyond bootstrap resume-tail. Orchestrator could skip re-check or pass wrong flags; bootstrap tests still pass; operators get stuck or duplicate snapshot/gh work. Add structural pins or a small routing fixture for sentinel path, re-check, and --resume-plan-tail args documented in SKILL.md.
- **Suggested revision**: Address the concern above.

### FINDING_3: risk-integration: skills/implement/SKILL.md:294-340
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No CI guard enforces single Bash bootstrap call for Step 0 #1-16 per plan acceptance. Future SKILL edits could reintroduce 16 separate Bash blocks without failing make lint. Extend test-implement-structure or halt-rate harness to assert one implement-bootstrap --up-to-phase plan block and ban retired prompt-side helpers outside dirty-tree recovery.
- **Suggested revision**: Address the concern above.

### FINDING_4: risk-integration: skills/implement/scripts/test-implement-bootstrap.sh:711-720
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Missing B3-plan symmetric to B2-plan for adopted-issue-is-pr on --up-to-phase plan. PR-target issue on plan phase might not be regression-protected against Phase 3 bail overwrite (low probability given should_run_phase_plan_materialize). Add B3-plan with LARCH_TEST_IS_PR=true and assert_not_contains for run-flags-persist-failed, dirty-tree, branch-create-failed.
- **Suggested revision**: Address the concern above.

### FINDING_5: risk-integration: skills/implement/scripts/test-implement-bootstrap.sh:836-878
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] B5-plan-green does not assert token-ledger/timing-ledger plan materialization marks in invoke log. Someone could remove absorbed marks from phase_plan_materialize without failing the green-path harness. Add assert_contains for token-ledger and timing-ledger Step 0 plan materialization mark lines in B5-plan-green invoke log.
- **Suggested revision**: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] risk-integration: skills/implement/scripts/test-implement-bootstrap.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] B8-plan-forked-target covers gh --repo upstream/repo only; forked gh without --repo path in implement-bootstrap.sh:567-568 is untested. Forked run omitting UPSTREAM_REPO might hit wrong gh default and fail in production without harness signal. Add B8-plan-forked-no-repo case asserting gh issue view without --repo.
- **Suggested revision**: Address the concern above.

