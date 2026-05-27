# Collaborative Sketches

The collaborative sketch phase is a diverge-then-converge process in `/design` where multiple agents independently propose architectural approaches before the full implementation plan is written. This prevents anchoring bias — where a single perspective locks in the direction before alternatives are considered.

## Why Sketches Exist

Without the sketch phase, the first idea considered tends to dominate the plan. By having multiple agents independently explore the design space, the system surfaces different perspectives early — when they can still influence the architectural direction — rather than waiting for review when the plan is already anchored.

## Sketch Agents

The sketch phase runs the topology selected by `/design`'s run-depth router. Each non-zero external slot has a Claude subagent fallback that activates when the respective tool is unavailable, preserving the configured lane shape.

### Simple Mode

For SIMPLE work, `/design` uses [0 sketch agents](topology.md#design.sketch.simple_slots). It writes sentinel synthesis artifacts and proceeds directly to plan writing; no collector runs on this path.

### Hard Mode

HARD mode keeps one slot per personality across a Cursor/Codex diagonal split (Cursor-Arch + Cursor-Edge + Codex-Innovation + Codex-Pragmatic):

| Agent | Harness | Role | Focus |
|---|---|---|---|
| **Cursor — Arch** (fallback: Claude) | Cursor | Architecture/Standards | Clean design, proper layering, reuse of existing libraries |
| **Cursor — Edge** (fallback: Claude) | Cursor | Edge-cases/Failure-modes | Boundary conditions, error handling, failure recovery |
| **Codex — Innovation** (fallback: Claude) | Codex | Innovation/Exploration | Creative alternatives, unconventional solutions, questioned assumptions |
| **Codex — Pragmatic** (fallback: Claude) | Codex | Pragmatism/Safety | Smallest change set, avoid regressions, protect existing features |

### Important Distinction

The sketch agents are **completely separate** from the plan-review agents that evaluate the plan later in `/design` Step 3. The sketch agents explore the design space; the plan reviewers validate the resulting plan using the panel described in [Review Agents](review-agents.md). They have different roles, different prompts, and serve different purposes.

## Per-Slot Fallback

When Cursor or Codex is unavailable, each affected slot falls back to a Claude subagent carrying the **same prompt** as the original external slot. This preserves the mode-specific topology above regardless of external tool availability.

## Fallback Behavior by Phase

The handling of unavailable external tools differs across workflow phases:

| Phase | Unavailable Tool Handling |
|---|---|
| **Sketch phase** (`/design`) | Per-slot Claude fallbacks with matching prompt — the mode-specific topology stays intact |
| **Plan review** (`/design`) | Per-archetype Cursor → Codex → Claude fallback chain; Codex generic → Claude — the configured panel stays intact |
| **Code review** (`/review`) | Cursor down → skip Cursor specialist slots; Codex down → skip Codex specialist slots; both down → no slots launched (voting skipped per threshold rules) |
| **Voting (plan review)** | Claude replacement voters used — always 3 voters. 3 voters: 2+ YES to accept; 2 voters: unanimous YES; <2 voters: voting skipped, all findings accepted |
| **Voting (code review)** | Claude + Codex + Cursor launched every round; Claude replacement voters fill unhealthy external slots so the panel stays at 3 voters when possible |
| **Dialectic debate** (`/design`) | **No Claude substitution for debaters** — when the assigned external tool (Cursor for odd-indexed decisions, Codex for even-indexed) is unavailable, that decision's debater bucket is skipped entirely and a `Disposition: bucket-skipped` resolution is written (synthesis decision stands). Intentional divergence from the rules above for debate execution only; see Step 2a.5 in `skills/design/SKILL.md` |
| **Dialectic judge panel** (`/design`) | **Claude replacements keep the panel shape intact** — the post-debate judge panel described in `skills/shared/dialectic-protocol.md` follows the repo-wide replacement-first pattern. When an external judge tool is unhealthy, a Claude Code Reviewer subagent replaces that slot. Judges merely adjudicate between pre-authored defenses — the no-Claude rule applies to adversarial debate execution only, not to adjudication. |

## How It Works

```text
flowchart TD
    START([Feature description]) --> TIER{Design tier}
    TIER -->|SIMPLE| SIMPLE_SENTINEL[Write SIMPLE sentinel artifacts]
    TIER -->|HARD| HARD_LAUNCH[Launch 4 personality sketches]
    HARD_LAUNCH --> HARD_WAIT[Wait for sketches]
    HARD_WAIT --> SYNTHESIS[Approach synthesis]
    SYNTHESIS --> CONTESTED{Contested decisions}
    CONTESTED -->|none| PLAN[Full implementation plan]
    CONTESTED -->|present| DIALECTIC[Dialectic debate]
    DIALECTIC --> PLAN
    SIMPLE_SENTINEL --> PLAN
    PLAN --> REVIEW[Full plan review panel]
```

1. **Parallel launch** — HARD launches all external and per-slot Claude fallback sketches simultaneously: all Cursor slots first (slowest), then all Codex slots, then any Claude fallback sketches. SIMPLE launches nothing and writes sentinel artifacts instead.

2. **Each agent produces** a short sketch covering:
   - Key architectural decisions and approach
   - Which files/modules to modify and why
   - Main tradeoffs to consider

3. **Synthesis** — After all sketches return, the orchestrating agent produces a synthesis that:
   - Identifies where approaches agree (likely the majority)
   - Identifies divergence points and makes reasoned calls with justification
   - Notes which ideas from each sketch are incorporated
   - (Regular mode only) Highlights personality-specific concerns: **Architecture/Standards**, **Pragmatism/Safety**, **Edge-case/Failure-mode**, **Innovation/Exploration**
   - (Quick mode) Attributes by tool (Cursor-Generic vs Codex-Generic)
   - (SIMPLE mode) Uses the sentinel `NO_SKETCHES_CLASSIFIED_SIMPLE` instead of fabricated agreement
   - Lists contested decisions in a structured format for the dialectic debate phase

4. **Dialectic debate and adjudication** (`/design` only) — If the synthesis identifies contested decisions (points where sketches genuinely diverged), the prioritized set is submitted to structured thesis/antithesis debates run on Cursor and Codex via deterministic per-decision bucketing. For each contested decision, a thesis agent defends the synthesis choice and an antithesis agent argues for the strongest alternative. Both run in parallel with codebase access. Successful debates are then forwarded to the binary judge panel described in `skills/shared/dialectic-protocol.md`, which casts `THESIS` / `ANTI_THESIS` votes on each decision. The orchestrator writes resolutions as directed by the panel, recording `Disposition: voted | fallback-to-synthesis | bucket-skipped | over-cap` per decision. This step is skipped when all sketches agree. See [Dialectic Debate](#dialectic-debate-design-only) below for details.

5. **Full plan** — The synthesis and any dialectic resolutions inform the complete implementation plan, which is then submitted to the validation panel described in [Review Agents](review-agents.md).

## Dialectic Debate (/design only)

> **Note**: This phase applies only to `/design`. `/research` does not include a dialectic debate step.

The dialectic debate phase adds reasoning depth on contested points without replacing the breadth-of-perspectives from the sketch phase. It addresses a specific weakness in the convergence step: when the synthesis identifies divergence points, the orchestrator would otherwise unilaterally resolve them — exactly where confirmation bias can creep in. Since Phase 3, adjudication between the two defenses is delegated to the judge panel rather than the orchestrator, further decorrelating the adjudication signal from the agent that produced the synthesis.

### When It Runs

The dialectic debate runs only when the synthesis in Step 2a.4 identifies genuine contested decisions — points where multiple sketches proposed fundamentally different approaches. If all sketches agreed, the debate is skipped entirely.

### How It Works

For each prioritized contested decision:

1. A **thesis agent** defends the approach chosen by the synthesis, arguing why it's the right call given the codebase and requirements
2. An **antithesis agent** attacks that choice, arguing for the strongest alternative, poking at hidden assumptions, and surfacing risks the synthesis glossed over

Both agents run in parallel and produce tagged structured output. An **eligibility gate** requires both sides to report `STATUS=OK` from the collector and pass the structural quality checks listed in `skills/shared/dialectic-protocol.md` before the decision is forwarded to the judge ballot. If either side fails the gate, the decision's `Disposition` is `fallback-to-synthesis` and the synthesis decision stands for that point.

After the eligibility gate, successful debates go to the binary judge panel (Claude Code Reviewer subagent + Codex + Cursor, with Claude replacements when externals are unhealthy). The panel reads an attribution-stripped ballot (Defense A / Defense B with deterministic position-order rotation across decisions) and casts one binary vote per decision: `THESIS` (the side defending the synthesis choice wins) or `ANTI_THESIS` (the alternative wins). The orchestrator writes resolutions as directed by the threshold rules in `skills/shared/dialectic-protocol.md`.

### Scope of Resolutions

Dialectic resolutions are **binding for Step 2b** (plan generation) only. They may be superseded by accepted findings from the Step 3 plan review. The finalized plan remains the sole canonical output.
