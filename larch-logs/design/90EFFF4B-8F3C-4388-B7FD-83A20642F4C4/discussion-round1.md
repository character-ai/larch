## Decision 1: Coverage scope
- **Question**: Which gaps should this design close?
- **Resolution**: Cover all three — invoke-plan-validator edge exits, read-budget remaining branches, and a defects-found / driver failure case.
- **Source**: user

## Decision 2: Fixture strategy
- **Question**: How should new full-tier cases be wired?
- **Resolution**: Reuse existing fixtures (e.g., `fixtures/validate-plan-commands/demo-plan.md` for the defects-found case; `parse-plan-commands/basic-plan.md` for the ok case).
- **Source**: user
