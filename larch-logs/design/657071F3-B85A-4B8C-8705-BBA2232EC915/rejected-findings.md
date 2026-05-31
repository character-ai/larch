### [Plan Review] FINDING_1

### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/ship-pr.sh:2724-2758
- **Concern**: Recovery waterfall edit anchored only on tier_rc!=0 continue path. Scenario: CI launchers exit 0 and encode agent failure in LAUNCHER_EXIT while tier_rc stays 0; surfacing only inside the block at 2745-2747 never runs and verify runs on a failed tier
- **Proposed resolution**: After each launcher esac (~2744), capture stdout, parse LAUNCHER_EXIT, and when tier_rc!=0 OR LAUNCHER_EXIT!=0 OR -s ${output}.stderr-tail: call _surface_ci_stderr_tail then recovery_waterfall_paths_delta_revert and continue before detached-head/verify


### [Plan Review] FINDING_6

### FINDING_6:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/ship-pr.sh:2728-2757
- **Concern**: Recovery-waterfall surfacing trigger is clear but insertion point is ambiguous. Scenario: CI launchers exit 0 while LAUNCHER_EXIT is non-zero; today only tier_rc -ne 0 reverts/continues—implementer who only augments that block never surfaces tails before verify
- **Proposed resolution**: Add an explicit post-launcher block (after capturing/parsing stdout, before detached-head/verify): if LAUNCHER_EXIT -ne 0 or -s "${output}.stderr-tail" then _surface_ci_stderr_tail "$output" and continue


