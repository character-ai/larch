## Decision 1: Fix 3 event-scope investigation in scope
- **Question**: Should the plan investigate whether <task-notification> fires UserPromptSubmit, and potentially redesign the circuit breaker to fire on Stop directly?
- **Resolution**: In scope. The Stop handler should emit a block directive when the counter exceeds threshold, working regardless of whether task-notification fires UserPromptSubmit.
- **Source**: user

## Decision 2: Fix 2 classification Read rate-limit in scope
- **Question**: Should hook-bg-poll-guard.sh deny tasks/<id>.output Reads after N empty reads?
- **Resolution**: In scope alongside Fix 1 (threshold reduction).
- **Source**: user

## Decision 3: All 4 fixes in scope
- **Resolution**: Fix 1 (threshold 5→3), Fix 2 (Read rate-limit), Fix 3 (Stop-handler block path), Fix 4 (doc update for silent yield contract).
- **Source**: user + codebase

2 decisions resolved (Fix 3 scope, Fix 2 scope). All 4 fixes confirmed in scope.
