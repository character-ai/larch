# Review Round 5

- Mode: `diff`
- 12 accepted, 10 rejected (9 exonerated)

## Accepted Findings

### FINDING_1: code-quality: scripts/ship-pr.sh:2645-2655
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Duplicate defer_push if/else arms set identical state after re-bump removal Future edit to one branch only leaves the other stale and confuses reviewers during CI-fix work Collapse to one state_set_many after force-push
- **Suggested revision**: Address the concern above.


### FINDING_11: risk-integration: Makefile:160 / agent-lint.toml:1020 / scripts/test-ship-pr-rebase.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Makefile shard 13 and agent-lint reference test-ship-pr-rebase.sh but the script is not committed on the branch. CI clone runs make test-harnesses-13 and fails because scripts/test-ship-pr-rebase.sh is missing. Commit scripts/test-ship-pr-rebase.sh (and contract doc) or remove Makefile/agent-lint entries until present.
- **Suggested revision**: Address the concern above.


### FINDING_12: risk-integration: plan acceptance / scripts/ship-pr.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] No harness automates the plan acceptance concurrency case (two disjoint PRs; second merges without rebase/re-bump). Regression restoring per-PR bump/CHANGELOG or unnecessary CI rebase can ship while make lint and listed harnesses stay green. Add a dual-branch offline harness or demote the acceptance item to documented manual-only verification.
- **Suggested revision**: Address the concern above.


### FINDING_14: risk-integration: scripts/ship-pr.sh:1086-1094 / scripts/ship-pr.sh:3245-3266
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Stale RESUME_PHASE tokens are cleared on bump entry but unknown --resume-phase step8b_rebase still aborts. Mid-upgrade resume with legacy --resume-phase step8b_rebase dies with unknown resume-phase. Harness stale-state tolerance; optionally alias legacy resume tokens in the resume-phase case arm.
- **Suggested revision**: Address the concern above.


### FINDING_19: risk-integration: scripts/ship-pr.sh:3245-3266
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Legacy --resume-phase step8b_rebase and step8_apply_bump_same_version hit die_usage unknown --resume-phase; only in-state RESUME_PHASE is cleared when entering run_bump_phase. Operator or automation resumes a pre-Phase-1 interrupted run with ship-pr.sh --resume-phase step8b_rebase after upgrading larch; ship-pr exits 2 before the state machine advances, leaving PHASE stuck and requiring manual state surgery. Add case arms mapping step8b_rebase|step8_apply_bump_same_version|bump to advance_phase bump (and clear stale CALLER_KIND), matching force-push-gate tolerance; pin with test-ship-pr-rebase.sh.
- **Suggested revision**: Address the concern above.


### FINDING_21: correctness: scripts/ship-pr.md:128
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Invariants claim REBASE_COUNT >= 5 but run_rebase_rebump enforces 20. Operator reads ship-pr.md invariants and expects stall after five rebases while the run continues rebasing until twenty, confusing retry-storm diagnosis. Update the invariant bullet to >= 20 or point to the code constant.
- **Suggested revision**: Address the concern above.


### FINDING_23: correctness: skills/shared/subskill-invocation.md:23
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Pattern B still lists /bump-version as a nested /implement child call after Phase 1 removed it. Contributors follow subskill-invocation.md and reintroduce /bump-version Skill calls from /implement. Update the Pattern B parenthetical to /review and /issue only, or add an explicit Phase 1 note that implement no longer nests bump-version.
- **Suggested revision**: Address the concern above.


### FINDING_24: architecture: scripts/implement-finalize.md:3
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Header still says Step 8 post-bump work though Phase 1 body describes rebase+push only. Operators assume postbump still performs version bump work. Rename header prose to post-ship/postbump (8b rebase + force-push) without post-bump wording.
- **Suggested revision**: Address the concern above.


### FINDING_28: **architecture** `scripts/ship-pr.sh:3245-3266` — Phase 1 only tolerates legacy `--resume-phase` values `force-push-gate` and `bump` (both route to `advance_phase bump`). Retired tokens `step8b_rebase` and `step8_apply_bump_same_version` are cleared from state only when `run_bump_phase` runs (`_clear_phase1_postbump_residue` at `1086-1095`), but if anything re-invokes `ship-pr.sh` with `--resume-phase step8b_rebase` or `--resume-phase step8_apply_bump_same_version` (stale automation, manual retry, or an orchestrator that copies persisted `RESUME_PHASE` into argv), the startup `case` hits the default arm and `die_usage "unknown --resume-phase"` exits **2** instead of degrading to the no-op bump path. That is weaker than the plan’s “tolerate-and-ignore” edge case for pre-Phase-1 state. **Suggested fix:** Extend the `3246` resume `case` to treat `step8b_rebase|step8_apply_bump_same_version|force-push-gate` like `bump` (advance to bump, clear `RESUME_PHASE`/`CALLER_KIND`, optionally log a one-line legacy-resume notice), and add a `test-ship-pr-rebase.sh` runtime case that seeds a pre-Phase-1 `ship-pr-state.sh` and asserts `--resume-phase step8b_rebase` does not exit 2.
- **Reviewer**: dyn-resume-compat-output.txt
- **Concern**: - **architecture** `scripts/ship-pr.sh:3245-3266` — Phase 1 only tolerates legacy `--resume-phase` values `force-push-gate` and `bump` (both route to `advance_phase bump`). Retired tokens `step8b_rebase` and `step8_apply_bump_same_version` are cleared from state only when `run_bump_phase` runs (`_clear_phase1_postbump_residue` at `1086-1095`), but if anything re-invokes `ship-pr.sh` with `--resume-phase step8b_rebase` or `--resume-phase step8_apply_bump_same_version` (stale automation, manual retry, or an orchestrator that copies persisted `RESUME_PHASE` into argv), the startup `case` hits the default arm and `die_usage "unknown --resume-phase"` exits **2** instead of degrading to the no-op bump path. That is weaker than the plan’s “tolerate-and-ignore” edge case for pre-Phase-1 state. **Suggested fix:** Extend the `3246` resume `case` to treat `step8b_rebase|step8_apply_bump_same_version|force-push-gate` like `bump` (advance to bump, clear `RESUME_PHASE`/`CALLER_KIND`, optionally log a one-line legacy-resume notice), and add a `test-ship-pr-rebase.sh` runtime case that seeds a pre-Phase-1 `ship-pr-state.sh` and asserts `--resume-phase step8b_rebase` does not exit 2.
- **Suggested revision**: Address the concern above.


### FINDING_3: code-quality: scripts/ship-pr.sh:3245-3266
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Retired --resume-phase values not accepted at CLI entry Operator or automation resumes with --resume-phase step8b_rebase after plugin upgrade; ship-pr dies before clearing stale state Map retired tokens to bump with warning or no-op clear per plan stale-key tolerance
- **Suggested revision**: Address the concern above.


### FINDING_5: code-quality: scripts/implement-finalize.sh:2
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Stale file header says post-bump Docs and new contributors assume version bump still runs in finalize Update header to post-ship / Step 8b wording
- **Suggested revision**: Address the concern above.


### FINDING_8: correctness: Makefile:564-565
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Makefile registers test-ship-pr-rebase in test-harnesses-13 but scripts/test-ship-pr-rebase.sh is not committed to the branch. make lint / test-harnesses-13 fails on clean checkout with missing script path. Commit scripts/test-ship-pr-rebase.sh or remove Makefile target until the harness is ready.
- **Suggested revision**: Address the concern above.


