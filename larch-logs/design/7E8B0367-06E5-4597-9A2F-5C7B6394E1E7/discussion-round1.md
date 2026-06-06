## Decision 1: Scope — both directions
- **Question**: Cover both candidate directions (remove auto-apply re-baselining + add cumulative drift guard), or just one?
- **Resolution**: Both. Remove inter-round auto-apply AND add the drift guard. Matches the full acceptance criteria in the issue.
- **Source**: user

## Decision 2: Review-loop shape after auto-apply removal
- **Question**: Once inter-round auto-apply is gone, should Step 3 stay multi-round (re-reviewing an unchanged plan) or collapse to a single review pass?
- **Resolution**: Single review pass per Step 3 entry. Gate B is the sole apply point. Matches the issue's parenthetical "a single review pass with no inter-round auto-revision". The multi-round inner loop, its convergence rule, and inter-round revision are retired.
- **Source**: user

## Decision 3: Drift-guard response
- **Question**: When the plan grows past the drift threshold vs the Step-2b baseline, hard-halt or flag-and-prompt the operator?
- **Resolution**: Flag + operator prompt (AskUserQuestion), and block any silent auto-continue. No unconditional hard halt. Matches "surface the drift to the operator instead of silently accreting".
- **Source**: user

## Decision 4: Fate of `--manual` / `-m` / `manual_gate_b`
- **Question**: With no auto-apply on either tier, what happens to the manual-mode flag and the `manual_gate_b` run-params field?
- **Resolution**: Remove entirely. Delete `--manual` / `-m` from the public argv parser, `manual_gate_b` from the run-params schema, and all references in `flags.md` / `SKILL.md` / `approval-gates.md`. Gate B always presents accepted findings for explicit operator choice.
- **Source**: user

## Decision 5: Drift baseline must be SIMPLE-capable (codebase finding)
- **Question**: Is a Step-2b baseline available on SIMPLE for the drift guard to compare against?
- **Resolution**: Not today. `design-postplan-emit.sh` snapshots `plan.txt-original` only when `WORKFLOW_PATH == HARD` (lines 457-458). `diff-lines.txt` is written on all tiers. The plan must capture a tier-agnostic baseline (plan body line count + diff estimate) right after the initial Step 2b plan write so the drift guard works on SIMPLE — the exact tier that motivated #3482.
- **Source**: codebase

## Hard constraints / non-goals (carried into the plan)
- **Must not break**: the issue-anchoring sibling change touches `plan-review-loop.sh` in a different region — coordinate edits to avoid self-conflict (issue Dependencies). The assessor-on-SIMPLE sibling is blocked by this and shares the `plan.txt-original` baseline.
- **Non-goal**: re-anchoring each review round to the issue (that is the issue-anchoring sibling's job). This issue only removes auto-apply and adds the drift guard.
- **Acceptance**: `make lint` green; existing harnesses (`test-plan-review-loop.sh`, `test-step3-review-cap.sh`, `test-design-structure.sh`, etc.) updated; new regression coverage for the drift guard.
