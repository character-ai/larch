## Decision 1: Clean-run confirmation note
- **Question**: When the file is present but a run has no deviations, confirm or stay silent?
- **Resolution**: Always emit a brief "consulted ARCHITECTURAL_GUIDELINES.md; no deviations" note at the surfacing points, even on clean runs. Proves the file was read; matches larch's auditability ethos.
- **Source**: user

## Decision 2: /implement deviation-warning home
- **Question**: Where should /implement surface deviation warnings (warnings only, no blocking gate)?
- **Resolution**: PR body + run summary. Durable and reviewer-visible; matches decision #4 ("deviation rationale lives in the plan or PR").
- **Source**: user

## Decision 3: Scope = mechanism + larch's own seed file only
- **Question**: What is in-scope vs out-of-scope for this issue?
- **Resolution**: In-scope: create `ARCHITECTURAL_GUIDELINES.md` at repo root with the seeded set from the issue; wire `/design` and `/implement` to consult it; absent-file no-op test; link from `AGENTS.md` canonical sources. Out-of-scope: companion audit/lint issues (#5000, #5001, #5002, #5003, #4997) and growing the seed list.
- **Source**: issue

## Decision 4: Future categories not seeded now
- **Question**: Should the sketched future categories be seeded in this issue?
- **Resolution**: No. "Contracts & boundaries", "Observability & auditability", and "Testing" are explicitly out-of-scope/future. Seed only the issue's current set (Python coding practices, Skill authoring & context economy, Enforcement philosophy).
- **Source**: issue

## Decision 5: Absent-file invariant (hard constraint)
- **Question**: What must not change when the file is absent?
- **Resolution**: Absent file means exact same behavior as today in both skills. This is the load-bearing invariant and must be test-covered.
- **Source**: issue

## Decision 6: Never auto-edit the file (non-goal)
- **Question**: May the skills modify the guidelines file?
- **Resolution**: No. `/design` and `/implement` never auto-edit `ARCHITECTURAL_GUIDELINES.md`. It is hand-maintained. Deviation rationale lives in the plan or PR, not in the file.
- **Source**: issue

## Decision 7: Both skills wired; surfacing points
- **Question**: Which skills change, and where do deviations surface?
- **Resolution**: Both `/design` and `/implement` are wired in this plan. `/design` surfaces deviations at proposal-approval (the Step 1d.7 outline-approval gate) and final-plan-approval (Gate C, Step 4b). `/implement` warns on deviations with no blocking gate.
- **Source**: issue + codebase (current gate structure)

## Decision 8: Guidelines are aspirational, not invariants
- **Question**: How binding are the guideline entries?
- **Resolution**: Aspirational goals only, not hard rules. The agent may deviate with judgment; all deviations are surfaced. Scope is restricted to non-deterministically-enforceable goals (anything a linter/hook/structural test can catch belongs in those, not here).
- **Source**: issue
