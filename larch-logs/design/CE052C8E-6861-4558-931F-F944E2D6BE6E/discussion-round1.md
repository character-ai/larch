# Design Discussion Round 1

## Decision 1: Plan source under --emergency
- **Question**: When --emergency is set, what plan source should /implement use?
- **Resolution**: Use larch:plan block if present in the issue body; otherwise fall back to the raw issue body (no validation gates).
- **Source**: user

## Decision 2: Preflight checks bypassed by --emergency
- **Question**: Which Preflight checks should --emergency bypass?
- **Resolution**: Bypass exactly three: (a) plan-block presence (BLOCK_PRESENT=false still proceeds), (b) plan-adequacy audit (AUDIT=refuse still proceeds), (c) clarify-state pending (needs-design-clarification label still proceeds). Semantic materiality / stale-plan notice is NOT bypassed — it still fires.
- **Source**: user

## Decision 3: Warning behavior
- **Question**: How loud should the bypass be?
- **Resolution**: Loud bold warning to chat AND structured entry in execution-issues.md for the run log.
- **Source**: user

## Decision 4: Mutual exclusion with other flags
- **Question**: How does --emergency interact with --forked, --merge, --draft?
- **Resolution**: --emergency is **mutually exclusive with --draft** only. It is **compatible** with --forked and --merge. Rationale: --draft indicates "not ready to land", which contradicts the fast-track emergency intent.
- **Source**: user

## Decision 5: Audit trail / persistence
- **Question**: How should --emergency be recorded for post-run inspection?
- **Resolution**: Persist `emergency_requested=true` in `run-params.json`; include in the final summary block; reflect in tracking-issue `larch:metadata` so post-merge auditors and history are aware.
- **Source**: user

## Hard constraints (must-preserve)
- Default behavior (without --emergency) is unchanged: all Preflight gates still fire.
- Semantic materiality / stale-plan notice still fires under --emergency.
- The flag is optional; current behavior is the default.
