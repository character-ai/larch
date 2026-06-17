# Review Round 2

- Mode: `diff`
- 1 accepted, 4 rejected (2 neutral)

## Accepted Findings

### FINDING_5: Pre-driver SKILL.md omits fail-closed halt on non-zero seeder exit
- **Reviewer(s)**: dyn-step8-routing-output.txt
- **Severity**: important
- **Concern**: Pre-driver Step 8 text says to skip the seeder when `ship-pr-state.sh` already exists, but does not state the plan’s fail-closed rule: a non-zero `step-8-seed-initial.sh` exit must stop the run before `python/cli.py oos file` and `step-8-ship.sh`. If the orchestrator misjudges absent/empty state, calls the seeder against a Step 5 stall seed, gets exit `2`, and still runs `oos file`, filing can proceed with missing or incomplete state (`REPO` / `ISSUE_NUMBER` empty in `python/oos_filer.py:733-737`), producing partial OOS evidence without durable disposition markers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-step8-routing-output.txt: Add explicit pre-driver ordering text: on any non-zero seeder exit, halt before `oos file` and `step-8-ship.sh`; invoke the seeder fence only when the state file is absent or empty.


