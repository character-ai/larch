## Decision 1: Fix approach
- **Question**: Which fix path (Option A wait $!, B PID check, C exec, or combined) should the sketches focus on?
- **Resolution**: Let sketches debate independently; resolve via dialectic.
- **Source**: user

## Decision 2: Scope of fix
- **Question**: ship-pr.sh only, all top-level Family B writers, or every background+monitor pair in the repo?
- **Resolution**: Top-level Family B writers only (ship-pr.sh, run-step5-review.sh, collect-agent-results.sh, dispatch-plan-voters.sh — run-step2-dispatch.sh is named in AGENTS.md but not present in the repo).
- **Source**: user

## Decision 3: Orphan cleanup
- **Question**: Are existing orphan ship-pr.sh processes in scope?
- **Resolution**: Out of scope. This issue is prevention only.
- **Source**: user

## Decision 4: Update BASH_AUTHORING.md §4 normative prose
- **Question**: Should §4 be updated to make the `wait $!` discipline normative for the background+monitor pair?
- **Resolution**: Yes. Update §4 so future skill authors follow it by default. Sweep SKILL.md / references/*.md fenced examples that copy the pair so they stay in sync.
- **Source**: user

## Decision 5: Extend lint-foreground-markers.sh
- **Question**: Should the linter enforce the `wait $!` line in fenced bash blocks and Family B writer shell scripts?
- **Resolution**: Yes. CI lint must require the wait line in every fence/script that matches a Family B anchor so regressions are caught automatically.
- **Source**: user

## Decision 6: Regression test
- **Question**: Should we add a regression test for the wait $! semantics?
- **Resolution**: Yes — add a focused offline harness (e.g., test-background-monitor-wait.sh) that simulates the orphan scenario: background a slow process, run a fast monitor that exits early, verify the parent shell waits for the background PID before exiting.
- **Source**: user

## Hard constraints (recorded for sketches)
- Must preserve breadcrumb-monitor.sh live-streaming semantics (Option C exec replacement is dispreferred by the issue body).
- Must not break the single-runner invariant or existing ship-pr.sh state-file contract.
- Bash 3.2 compatibility for any new test harness (per BASH_AUTHORING.md §3).
- Linter changes must not break existing pre-commit hooks / Makefile targets (relevant-checks.sh / make lint).

## Non-goals
- No changes to non–Family B background launches (sketch agents, reviewers via launch-* helpers).
- No orphan reaper / process cleanup at session teardown.
- No change to Option C (exec replacement) approach (loses live streaming).
