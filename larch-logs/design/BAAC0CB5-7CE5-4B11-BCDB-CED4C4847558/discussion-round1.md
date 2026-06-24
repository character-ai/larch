## Decision 1: Deep external debate path
- **Question**: Build the opt-in heavy external (Codex/Cursor per-side) debate path now, or ship cheap parallel-Claude-subagent debate only and defer deep?
- **Resolution**: Cheap path only. Ship the cheap parallel-Claude-subagent debate. Defer the external Codex/Cursor per-side waterfall to a follow-up (OOS for this change).
- **Source**: user

## Decision 2: On-demand "debate this decision" affordance
- **Question**: Add the manual "debate this decision" gate affordance (Recommended-shape item 4) now, or defer it?
- **Resolution**: Include the on-demand affordance now. The operator can force a focused dialectic on one decision at a gate even when auto-detection stays quiet.
- **Source**: user

## Decision 3: Cost-discipline hard constraint
- **Question**: What cost envelope must the revival hold?
- **Resolution**: Hard constraint. Runs with no contested fork pay near-zero overhead. Detection must be cheap (fold into work Step 2b already does, not a separate classifier pass). Debate runs in subagents; only a compact per-fork digest reaches the orchestrator. Defer loading any large protocol/choreography reference until a contested decision is confirmed. Add no sequential orchestrator turns and no new halts; piggyback existing gates and collect parallel subagent debate in a single background wait.
- **Source**: codebase (feature-description.txt)

## Decision 4: No tier revival, no new pause
- **Question**: May the change reintroduce the SIMPLE/HARD tier or a mandatory pre-draft pause?
- **Resolution**: No. Do not revive the SIMPLE/HARD tier or any mandatory pre-draft pause. Cheap-default plus opt-in-deep plus a hard 1-2 decision cap is the guardrail.
- **Source**: codebase (feature-description.txt)

## Decision 5: Detection bar and cap
- **Question**: When should a fork fire?
- **Resolution**: Fire only on genuine bistable architectural forks: two concrete approaches with a material, non-obvious tradeoff. Scope questions stay in the clarify loop; pure internal preferences stay with the drafter. Strict "two concrete approaches + real tradeoff" bar. Cap debate to the top 1-2 decisions.
- **Source**: codebase (feature-description.txt)

## Decision 6: Documentation reconciliation
- **Question**: What stale dialectic references must this change reconcile?
- **Resolution**: Reuse `skills/shared/dialectic-protocol.md` as-is (adjudication core is reusable). Reconcile the stale Step 2a.5 debater note in `SECURITY.md`. Rewire dialectic references so they describe the new clarifier flow rather than the removed decider flow.
- **Source**: codebase (feature-description.txt)

## Out of scope for Round 1 (delegated to /design at Step 2b / Step 3)
- Exact gate placement (Step 1d.7 vs Gate C), the detection mechanism, the default debater backend, artifact flow, and the public flag surface. The issue explicitly assigns these to /design to determine; they are architectural and are resolved during plan drafting and review, not by operator scope questions.
