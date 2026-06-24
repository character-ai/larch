## Proposed Design Outline

### Goals
- Re-introduce dialectic as an operator-facing clarifier: detect genuine bistable architectural forks, steelman both sides, adjudicate, recommend. Operator is judge of last resort.
- Hold near-zero overhead when no fork fires. Run debate in subagents; only a compact per-fork digest reaches the orchestrator.
- Reuse `skills/shared/dialectic-protocol.md` adjudication core as-is; reconcile stale dialectic references.

### Non-goals
- No SIMPLE/HARD tier revival, no mandatory pre-draft pause, no new orchestrator halts.
- No external Codex/Cursor per-side deep path in this change (deferred to a follow-up; OOS).
- No autonomous decider: dialectic never silently picks. It recommends; the operator decides at an existing gate.

### Approach sketch
- Detect forks cheaply as Step 2b drafter self-declaration, folded into existing drafting work. Hard cap at top 1-2 decisions; strict "two concrete approaches + real tradeoff" bar.
- Run the cheap debate in parallel Claude subagents in a single background wait; emit one compact per-fork digest block.
- Surface each fork at an existing gate (likely Gate C for post-draft forks; Step 1d.7 considered for pre-draft) by piggybacking the existing AskUserQuestion. Operator accepts the lean, flips it, or opens discussion.
- Add an on-demand "debate this decision" affordance at the gate so the operator can force a focused dialectic.
- Put detection/debate/digest orchestration logic in Python behind `cli.py` (G-Skill-2). Defer loading the protocol/choreography reference until a fork is confirmed (G-Skill-1).

### Surfaces in scope
- `skills/design/SKILL.md` and `skills/design/references/` (new dialectic clarifier reference).
- `skills/shared/dialectic-protocol.md` (rewire into the clarifier flow).
- `python/` (detection signal, debate dispatch, digest, plus tests).
- `SECURITY.md` (reconcile the stale Step 2a.5 debater note).

### Open questions
- Exact gate placement (Step 1d.7 vs Gate C) and the detection-signal wiring are delegated to plan drafting and review; the cheap default leans post-draft at Gate C.
