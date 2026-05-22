# Review Round 3

- Mode: `diff`
- Accepted findings: 5
- Rejected findings: 0
- Exonerated findings: 19
- Neutral findings: 0

## Accepted Findings

### FINDING_11: risk-integration: scripts/test-ship-pr.sh:883-935
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] No test asserts bump-branch-guard on --resume-phase bump re-entry. Resume-only regression could reintroduce bump-on-wrong-branch without failing the suite. Add a resume-phase bump harness case that expects STALL_STEP=bump-branch-guard before bump stubs.
- **Suggested revision**: Address the concern above.


### FINDING_19: risk-integration: scripts/test-ship-pr.sh:883-905
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] bump_branch_guard_main/master likely hit mismatch before the non-forked default-branch prohibition. Removing or breaking the third guard in run_bump_phase (lines 829-838) could still leave tests passing while allowing a classified bump on an aligned local main when FORKED_TARGET is false. Add tests with checkout matching BRANCH_NAME=main or master and FORKED_TARGET false to assert exit 4 and bump-branch-guard via the intended code path.
- **Suggested revision**: Address the concern above.


### FINDING_20: correctness: skills/implement/scripts/step2-implement.sh:293-325
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Spawn branch uses rev-parse --abbrev-ref; detached HEAD yields SPAWN_BRANCH=HEAD so main-branch-prohibited does not run. Issue-anchored external implementer could run on detached HEAD; post-dispatch SKILL assertion may also be skipped or behave differently vs named branch. Treat HEAD spawn or symbolic-ref failure as fail-closed for issue-anchored runs or align capture with git-current-branch.sh semantics.
- **Suggested revision**: Address the concern above.


### FINDING_25: correctness: scripts/ship-pr.sh:829-838
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] FORKED_TARGET=true allows bump when BRANCH_NAME is main or master if checkout matches, which is absent from the plan guard snippet and contradicts the feature_description acceptance that BRANCH_NAME main or master must stall before bump. Mis-set FORKED_TARGET=true on a mistaken local main workflow can still reach version bump classify or apply, weakening the acceptance that main or master BRANCH_NAME always stalls before bump. Update the plan and acceptance to explicitly allow the fork carve-out, or remove the carve-out and require fork flows to use non-protected BRANCH_NAME or additional fork evidence beyond state alone.
- **Suggested revision**: Address the concern above.


### FINDING_26: risk-integration: skills/implement/scripts/step2-implement.sh:299-325
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] main-branch-prohibited only fires for issue-anchored tmpdirs (parent-issue ISSUE_NUMBER or session-env present) and non-forked runs, not unconditionally on main or master as in the plan Guard 2 snippet. External Step 2 on main with a tmpdir that has neither session-env nor parent-issue ISSUE_NUMBER never hits main-branch-prohibited and can still launch the implementer, leaving a gap relative to the unconditional plan guard. Match the plan with unconditional bail on main or master, or document the narrower scope in the plan and add tests for the unanchored path if it must remain allowed.
- **Suggested revision**: Address the concern above.


