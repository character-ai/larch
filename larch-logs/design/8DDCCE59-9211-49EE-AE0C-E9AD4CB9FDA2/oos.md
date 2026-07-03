### FINDING_1: Register `difficulty resolve-panel`
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The CLI dispatch table is missing the `difficulty resolve-panel` entry, so shell wrappers and `/review` cannot invoke the resolver at runtime.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add `### UPDATED: python/larch/cli.py` registering `("difficulty", "resolve-panel")` to `resolve_panel_main` (or the planned entrypoint) in both dispatch maps, matching G-CLI-1.
  - From Cursor-Pragmatic: Add `### UPDATED: python/larch/cli.py` and register `("difficulty", "resolve-panel")` to `resolve_panel_main` per G-CLI-1, with a focused registry test if the repo pattern requires it.


Vote tally: YES=1 NO=1 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_2: Persist implement difficulty override through run-flags
- **Reviewer(s)**: Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: The operator difficulty override is planned to ride through `persist-run-flags`, but the current run-flag key set excludes it. As a result, bootstrap can write the override and Step 5 still cannot recover it from `run-flags.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Extend `persist_run_flags_main` with optional `--difficulty`, add `DIFFICULTY_OVERRIDE` to `RUN_FLAG_KEYS`, thread the flag through `bootstrap._persist_run_flags` / `invoke_main`, and read it in `step-5-review.sh` / `step-5-resume.sh`.
  - From Codex-Innovation: Extend session persist-run-flags and RUN_FLAG_KEYS for DIFFICULTY_OVERRIDE, pass it from bootstrap, and have Step 5 read that exact key
  - From Cursor-Pragmatic: Extend `RUN_FLAG_KEYS` and `persist_run_flags_main` with optional `--difficulty-override` (empty or `TRIVIAL|MODERATE|HARD`); thread it from `bootstrap.invoke` / `_persist_run_flags`; document the same contract in `bootstrap.py` and `skills/implement/scripts/step-0-bootstrap.sh`. Alternatively drop the run-flags read path and have Step 5 read override state only from `difficulty-rating.json`, but pick one source and wire it end-to-end.
  - From Cursor-Requirements: Add `DIFFICULTY_OVERRIDE` to `RUN_FLAG_KEYS`, extend `persist_run_flags_main` and `bootstrap invoke/BootstrapOptions`, and thread the value through `step-0-bootstrap.sh` like other run flags.


Vote tally: YES=1 NO=1 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_3: Preserve `difficulty_override` on run-params refresh
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: `write-run-params` rebuilds `run-params.json` from the current booleans only, so a stored `difficulty_override` is lost on init or resume refresh when no fresh tier flag is provided.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: When `--difficulty` is omitted, read the existing output file and carry forward `difficulty_override`; only replace it when a new valid tier is passed. Mirror resume semantics in `design_router._merge_router_flags` or stop full-replacing on resume.
  - From Cursor-Pragmatic: When `--difficulty` is absent, read existing run-params.json and carry forward difficulty_override; when present, replace it. Extend `_merge_router_flags` (or equivalent) so resume paths preserve the key unless a new valid `--difficulty` is supplied.
  - From Cursor-Requirements: When `--difficulty` is absent, read the existing file and carry `difficulty_override` forward; only overwrite it when a new valid tier is passed. Mirror the resume rule already stated for `route_main`.


Vote tally: YES=1 NO=1 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_7: Preserve `override_source` during record refresh
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: Log-flush record refresh drops `override_source` from the existing difficulty record, so later writes can erase the operator origin even when the rest of the difficulty state is preserved.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Pass through `override_source` (and post-escalation `applied_tier`) from the existing record, or route refresh through the shared merge helper planned for `write-record`.


Vote tally: YES=1 NO=1 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_14:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:10-12,37-45
- **Concern**: [SCOPE-REDUCTION] Audit still overrides an explicit operator difficulty override. Scenario: An operator runs /implement, /review, or /design with --difficulty TRIVIAL to force the cheap tier, but the planned 1:30 audit upgrades it to HARD even though the scope says --difficulty override wins and prior accepted findings required preserving that contract
- **Proposed resolution**: Do not run the audit when override_source=operator; log override_source=operator and keep the operator-selected panel tier


Vote tally: YES=1 NO=1 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_15:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:14,111-113
- **Concern**: [SCOPE-REDUCTION] Design escalation still skips the next-tier contract. Scenario: /design at TRIVIAL with two high accepted findings jumps directly to HARD, skipping MODERATE, despite the scope saying escalated rounds run the next tier's full panel
- **Proposed resolution**: Make design escalation use the same one-tier ladder as code review; TRIVIAL escalates to MODERATE and MODERATE escalates to HARD


Vote tally: YES=1 NO=1 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_18:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:12
- **Concern**: [SCOPE-REDUCTION] Operator overrides are still audit-upgraded despite the issue contract that --difficulty wins. Scenario: A user runs /implement --difficulty TRIVIAL to force the cheap tier, the 1:30 audit fires, and the plan runs HARD anyway while claiming the override won
- **Proposed resolution**: Make maybe_audit_upgrade skip when override_source=operator; log override_source=operator and do not set audit_upgrade for explicit overrides


Vote tally: YES=1 NO=1 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_19:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:14
- **Concern**: [SCOPE-REDUCTION] The prior design-escalation finding is not fixed because /design still jumps not-HARD directly to HARD. Scenario: /design --difficulty TRIVIAL with two high findings in round 1 skips the MODERATE tier and immediately unlocks the HARD model and cap, over-serving the next-tier ladder
- **Proposed resolution**: Use next_tier for design too; TRIVIAL escalates to MODERATE first, and HARD is reached only from a later substantial MODERATE round


Vote tally: YES=1 NO=1 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_21:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:10-12
- **Concern**: [SCOPE-REDUCTION] Prior override finding remains incomplete: audit still upgrades explicit operator overrides. Scenario: An operator runs /design --difficulty TRIVIAL to force the cheap tier, the 1:30 audit fires, and the plan runs HARD anyway, violating the acceptance that --difficulty override wins and over-serving the requested minimum-change control
- **Proposed resolution**: Make operator overrides disable audit upgrades for that run, while still logging override_source=operator; update helper behavior, docs, and tests that currently require override plus audit to run HARD


Vote tally: YES=1 NO=1 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_22:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:14,113,257
- **Concern**: [SCOPE-REDUCTION] Prior design-escalation finding remains incomplete: TRIVIAL design still jumps directly to HARD. Scenario: A TRIVIAL design round with two high accepted findings skips MODERATE and unlocks HARD model role and cap immediately, contradicting the next-tier escalation contract and adding unnecessary cost
- **Proposed resolution**: Use next_tier for design too; TRIVIAL escalates to MODERATE even if the v1 panel shape is identical, and only MODERATE escalates to HARD


Vote tally: YES=1 NO=1 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### OOS_1: [SCOPE-REDUCTION] Adding a new design dispatch shell harness duplicates existing coverage.
- **Description**: [SCOPE-REDUCTION] Adding a new design dispatch shell harness duplicates existing coverage.. Scenario: The plan lists `skills/design/scripts/test-dispatch-plan-review-panel.sh`, which does not exist; `make test-dispatch-plan-review-panel` already runs `python/tests/review/test_plan_review_panel.py`.
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/scripts/test-dispatch-plan-review-panel.sh
- **Phase**: design

Vote tally: YES=1 NO=1 JUDGE_ERROR=0 Result=neutral

