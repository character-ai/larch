## Goal
Soften ask-on-doubt default in /design Step 1c and /implement Step 2 opportunistic questions

## Implementation Plan
Soften suppression bias in /design Step 1c and /implement Step 2 AskUserQuestion gates.


### Goal
Flip the default disposition from "suppress unless genuinely ambiguous" to "ask on any doubt" in two specific locations, without changing caps, short-circuits, or auto_mode behavior.

### Change 1 — `skills/design/references/discussion-rounds.md` Step 1c

**File**: `skills/design/references/discussion-rounds.md`
**Location**: The `<!-- step:1c — Clarifying Questions (auto_mode=false body) -->` block, specifically the Guidelines bullet that currently reads "Only ask questions when there is genuine ambiguity..."

**Current** (line 23):
```
- Only ask questions when there is genuine ambiguity — do NOT ask trivially answerable questions or re-confirm what is already clear.
```

**New** (replace that bullet with ask-on-doubt wording):
```
- If you have any doubt about scope, requirements, or what 'done' means, ask. This is the highest-value question point in the entire workflow — answers here reshape what the sketch agents explore. The cost of one extra clarifying question is small; anchoring sketches on the wrong interpretation is large. Suppress only when the feature description is fully unambiguous.
```

Keep line 24 (`- Batch questions into a single AskUserQuestion call with 1-4 questions...`) unchanged.
Keep line 25 (`- If the feature description is clear and unambiguous, proceed to Step 1d.`) unchanged.

### Change 2 — `skills/implement/SKILL.md` Step 2 "Opportunistic questions"

**File**: `skills/implement/SKILL.md`
**Location**: Line 1229, the "Opportunistic questions" paragraph.

**Current**:
```
**Opportunistic questions** (`auto_mode=false` only): before edits, if the plan leaves genuinely ambiguous choices, batch 1-4 into a single `AskUserQuestion`. Only ask when the ambiguity cannot be resolved from the plan, codebase, or CLAUDE.md. When `auto_mode=true`, proceed with best judgment.
```

**New**:
```
**Opportunistic questions** (`auto_mode=false` only): before edits, if the plan leaves ambiguous choices — interpretations the plan does not pin down and the codebase does not unambiguously dictate — batch 1-4 into a single `AskUserQuestion`. Ask freely about plan ambiguities; do NOT ask about whether to do the plan, scope, or capacity (see "No mid-run scope re-litigation"). When `auto_mode=true`, proceed with best judgment.
```

Note: The existing "No mid-run scope re-litigation" paragraph immediately precedes the change site (line 1229). The new wording explicitly cross-references it so the guardrail remains visible and the two rules work together.


## Test plan
- Run `/relevant-checks` after edits (pre-commit + agent-lint).
- Grep both files to confirm old suppression-biased phrases are gone.
- Confirm 1-4 batch cap and auto_mode=true branch are unchanged.
