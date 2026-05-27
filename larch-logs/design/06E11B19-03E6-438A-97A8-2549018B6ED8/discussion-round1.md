## Decision 1: Trigger scope
- **Question**: Should the new outline-after-synthesis behavior fire only in brainstorm mode, or always?
- **Resolution**: Always — fire on every `/design` run regardless of `--brainstorm`. Justification: "the outline would be very helpful, preceding the detailed plan, which is quite unreadable on average."
- **Source**: user (Step 1c Q4, revised by interrupt)

## Decision 2: Re-entry policy
- **Question**: When the user later picks "Discuss further" (Gate C(b)) or "Re-run review panel" (Gate C(c)) so `/design` re-enters discussion or review after a plan has been written, should the outline-approval gate re-fire too?
- **Resolution**: One-shot per `/design` run — outline-approval fires once, before sketches; subsequent Gate A / Gate B / Gate C re-entries handle their own loops without re-generating an outline.
- **Source**: user (Step 1d Q1)

## Decision 3: Outline-approval gate placement vs Gate A
- **Question**: Does the new outline-approval gate (Approve outline / Refine outline / Cancel) co-exist with, or replace, the existing first-time Step 1e Gate A prompt?
- **Resolution**: The outline-approval gate **replaces** Step 1e Gate A's first-time-entry prompt (Shape 1: "Ready for review / Discuss more"). Gate A's Shape 2 (the 3-option re-entry prompt with "Show latest design proposal" used after Gate B(c) / Gate C(b)) is unchanged. Justification: avoid back-to-back prompts asking conceptually overlapping questions; "Approve outline" subsumes "Ready for review", "Refine outline" subsumes "Discuss more".
- **Source**: codebase (`skills/design/references/approval-gates.md` — Gate A's two-shape design already distinguishes first-time from re-entry; new gate slots cleanly into the first-time slot)

## Decision 4: Outline position in non-brainstorm mode
- **Question**: Where in the `/design` flow does the outline-approval step run when `brainstorm_requested=false`?
- **Resolution**: A new step (numbered between 1d and 1e — e.g., `1d.7`) fires after Step 1d Round 1 settles. In brainstorm mode the same step runs after Step 1d.5 brainstorm synthesis. In both modes it runs immediately before Step 1e Gate A on first entry. Justification: keeps user's "decide based on synthesis + outline" UX intact in brainstorm mode, and provides a symmetric early-direction decision point in non-brainstorm mode (matches Step 1c Q1 answer "the place that currently outputs Brainstorm Synthesis").
- **Source**: user (Step 1c Q1) + symmetry derivation

## Decision 5: Outline persistence
- **Question**: Is the outline persisted to a session file, or shown in chat only?
- **Resolution**: Persist to `$DESIGN_TMPDIR/design-outline.md`. The "Refine outline" loop needs a stable artifact to mutate; downstream debugging benefits; and the file is naturally cleaned up by Step 6 (no operational cost).
- **Source**: opinionated default (driven by Step 1c Q3 "Refine outline" semantics — Refine implies a mutable artifact)

## Decision 6: larch:plan / GitHub integration
- **Question**: Should the outline be included in the `larch:plan` block written to GitHub at Step 5c?
- **Resolution**: No — session-internal only. `composed-plan.md` continues to contain `## Plan` + `## Acceptance` + `diff_lines:` trailer exactly as today. The outline serves an in-session UX role; `/implement` reads the full plan, not the early outline.
- **Source**: opinionated default (minimum-viable scope; avoids changing Step 5c's wire format)

## Decision 7: Outline content level
- **Question**: How detailed should the outline be (per Step 1c Q2)?
- **Resolution**: Concise short bulleted lists, maximally simple but complete: Goals (2-3 bullets) / Non-goals (2-3 bullets) / Approach sketch (3-5 bullets) / Files or surfaces in scope (list, conceptual not full paths required) / Open questions (1-3 bullets). Target ~15-25 lines total. No prose paragraphs.
- **Source**: user (Step 1c Q2 — "(1) but more concise, with a set of short bulleted lists, ideally, with maximally simply but complete text")

## Decision 8: Refine outline mechanism
- **Question**: How does "Refine outline" work mechanically?
- **Resolution**: After user picks Refine, the orchestrator asks the user (free-form) what to change ("What would you like to refine? Add ideas, remove items, adjust direction, etc."). The main agent then mutates `design-outline.md`, prints the updated outline, and re-fires the same Approve/Refine/Cancel prompt. Loop continues until Approve or Cancel.
- **Source**: opinionated default (mirrors brainstorm.md's free-form discussion loop pattern — minimal new machinery)
