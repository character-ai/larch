## Decision 1: Gap-fill scope
- **Question**: Should REPO gap-fill from route-state apply on fresh explicit-issue invocations?
- **Resolution**: No. Gap-fill should only run when ISSUE_NUMBER is also missing (true resume-like paths). On fresh calls with an explicit issue number, REPO must come from `resolve_repo()`.
- **Source**: codebase (lines 310-313 of design_step0.py; the `or` condition always fires because REPO is never set before `resolve_repo()` runs)
