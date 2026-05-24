## Decision 1: "Main agent" definition
- **Question**: What does "fall back to the main agent ASAP" mean operationally? The current waterfall already includes Claude as tier 3 (cursor → codex → claude).
- **Resolution**: Exit ship-pr.sh fix-loop entirely; outer /implement handles. The fix-loop does NOT skip to the in-script Claude tier — it terminates with a bail and returns control to the outer orchestrator.
- **Source**: user

## Decision 2: Health discriminator signal
- **Question**: What runtime signal should ship-pr.sh use to classify a first-fixer failure as "unavailability/health" (apply waterfall) vs "other" (skip waterfall)?
- **Resolution**: `LAUNCHER_EXIT` KV from launcher stdout. Each `launch-{cursor,codex}-ci.sh` exposes a stable taxonomy distinguishing "tool unavailable / login expired / health probe failed" from "tool ran but failed for another reason." run_ci_fix_vendor reads the KV to decide waterfall vs bail.
- **Source**: user

## Decision 3: Policy trigger scope
- **Question**: Does the policy apply to every entry into run_ci_fix_vendor, or only the very first invocation in a ship-pr.sh run?
- **Resolution**: Every entry — first-tier-only is the trigger. On EACH call to run_ci_fix_vendor, the first tier (cursor) is "the first fixer." If cursor fails non-health, skip the rest of the waterfall (no codex, no claude tier) and bail. Symmetric across FIX_ATTEMPTS=0,1,2 iterations.
- **Source**: user

## Decision 4: Exit code & BAIL_REASON
- **Question**: What exit code and BAIL_REASON should ship-pr.sh emit when the new policy fires?
- **Resolution**: Reuse exit 3 (`needs_user_bail_reason` path) with a NEW reason token added to the allowlist (working name: `first-fixer-non-health`; final token TBD by implementer — see ship-pr.sh:1228). No new top-level exit code is introduced.
- **Source**: user

## Decision 5: Scope of policy
- **Question**: Does the same policy apply to other fallback waterfalls in ship-pr.sh (rebase conflict resolution `run_rebase_rebump`, `run_recovery_waterfall`), or strictly to `run_ci_fix_vendor`?
- **Resolution**: Strictly `run_ci_fix_vendor` only. Rebase conflict resolver (cursor → codex branch in run_rebase_rebump ~line 2137) and `run_recovery_waterfall` keep their existing fallback behavior unchanged. Smallest blast radius.
- **Source**: user

## Decision 6: Post-bail behavior in /implement
- **Question**: After ship-pr.sh bails early with the new BAIL_REASON, what should /implement orchestrator do?
- **Resolution**: /implement Step 8+ catches the new bail reason and attempts a main-agent (Claude tool-call) fix at the orchestrator level, then re-invokes ship-pr.sh. This adds new dispatch logic to /implement Step 8 to recognize and handle the `first-fixer-non-health` BAIL_REASON.
- **Source**: user
