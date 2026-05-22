# Discussion Rounds Reference

**Consumer**: `/design` Steps 1c, 1d, and the post-plan discussion sub-round body invoked by Step 1e Gate A on re-entry from Gate B(c) / Gate C(b).

**Contract**: owns the three discussion-round bodies (Step 1c clarifying questions, Step 1d round 1, and the post-plan Round 2 body) with their decision-tree walks, question caps, output schemas (`$DESIGN_TMPDIR/discussion-round1.md`, `$DESIGN_TMPDIR/discussion-round2.md`), and the terse-answer rule. Round 2 is no longer an auto-step at Step 3.5 — Step 3.5 is now Gate B (the post-review chooser, see `approval-gates.md`). The Round 2 body remains the normative template for the discussion sub-round that Gate A executes on each "Discuss more" iteration when re-entered post-plan.

**When to load**: before executing Steps 1c, 1d, or a Gate A discussion sub-round (the Round 2 body in the last section).

**Binding convention**: single normative source for discussion-round behavior (decision-tree walk, question caps, output schemas, terse-answer rule).

---

<!-- step:1c — Clarifying Questions -->

Before launching the expensive collaborative sketch phase, use `AskUserQuestion` to clarify any ambiguities in the feature description. This is the highest-value question point — answers here reshape what the sketch agents explore.

Consider asking about:
- **Scope boundaries**: What is explicitly in-scope vs. out-of-scope? Are there related changes the user does NOT want?
- **Key decisions**: When there are meaningful alternatives (e.g., different architectural approaches, different file organization), present the options and ask which direction to take.
- **Unclear requirements**: Any aspect of the feature description that is vague, could be interpreted multiple ways, or has implicit assumptions.

**Guidelines**:
- If you have any doubt about scope, requirements, or what 'done' means, ask. This is the highest-value question point in the entire workflow — answers here reshape what the sketch agents explore. The cost of one extra clarifying question is small; anchoring sketches on the wrong interpretation is large. Suppress only when the feature description is fully unambiguous.
- Batch questions into a single `AskUserQuestion` call with 1-4 questions rather than multiple sequential calls.
- If the feature description is clear and unambiguous, proceed to Step 1d.

After the user responds, incorporate their answers into your understanding of the feature for all subsequent steps.

---

<!-- step:1d — Design Discussion Round 1 -->

Before launching the expensive collaborative sketch phase, stress-test the feature's scope and requirements by walking through the decision tree one question at a time. This is a deeper, sequential interrogation that resolves dependencies between decisions — each answer may reshape subsequent questions.

## Behavior

The orchestrator identifies key **scope and requirements decisions** from the feature description by exploring the codebase (Read/Grep/Glob). It builds a mental decision tree covering:
- **Scope boundaries**: What is explicitly in-scope vs. out-of-scope?
- **Hard constraints**: What must not break? What existing behavior must be preserved?
- **Non-goals**: What does the user explicitly NOT want?
- **Must-have requirements**: What is the minimum viable outcome?

Then walk each branch one question at a time via sequential `AskUserQuestion` calls, providing a **recommended answer** for each question. If a question can be answered by exploring the codebase, do so and report the finding instead of asking the user.

**Explicit prohibition**: Do NOT ask about implementation approach, architectural preferences, library choices, or file organization. Those decisions belong to the sketch phase (Step 2a). Round 1 is strictly requirements/scope clarification.

## Short-circuit

If the feature is straightforward with fewer than 2 scope decision branches, print `⏩ 1d: discussion r1 — no scope decisions require discussion (<elapsed>)` and proceed to Step 1e (Gate A). Step 1e always fires after Step 1d, including on this short-circuit path — users may still pick "Discuss more" to add context before sketches.

## Output

Write resolved decisions to `$DESIGN_TMPDIR/discussion-round1.md` using a simple Q&A format:

```markdown
## Decision 1: <short title>
- **Question**: <the question asked>
- **Resolution**: <the answer — from user or codebase>
- **Source**: user / codebase
```

This file captures scope boundaries and hard constraints only — NOT architectural preferences.

## Cap

At most **7 `AskUserQuestion` calls** in this step. If more than 7 decision branches remain after 7 questions, print: `⏩ Remaining scope questions deferred to implementation.` and proceed to Step 1e (Gate A) — users may pick "Discuss more" there to surface any deferred branches before sketches launch.

## Terse answers

If the user gives a terse or non-responsive answer (e.g., "I don't know", "your recommendation is fine", "sure"), accept the recommended answer and move on without re-asking.

Record `<N>` decisions resolved.

---

<!-- post-plan discussion sub-round body (invoked from Step 1e Gate A on re-entry; the legacy <!-- step:3.5 marker is intentionally retained below for tooling that anchors on it) -->

<!-- step:3.5 — Post-Plan Discussion Sub-Round body (referenced from Gate A re-entry) -->

After the plan has been reviewed (and possibly partially revised via Gate B), stress-test the remaining design decisions that were either (a) not covered in Round 1, or (b) deemed suboptimal by reviewers, or (c) introduced by the plan itself (decisions that didn't exist at the feature-description stage). This body is invoked from Step 1e Gate A on each re-entry from Gate B(c) "switch to discussion mode" or Gate C(b) "discuss further" — it is no longer an auto-step.

## Inputs

Read the following artifacts:
- `$DESIGN_TMPDIR/discussion-round1.md` — If it exists and is non-empty, use it to identify decisions already covered in Round 1 (avoid re-asking). **If it does not exist or is empty** (Round 1 short-circuited or was skipped), treat all candidate decisions as uncovered by Round 1 and proceed normally.
- `$DESIGN_TMPDIR/plan.txt` — The latest implementation plan (initial Step 2b write, or with any Gate B applied findings on a post-plan re-entry). Read this file instead of retrieving the plan from conversation context.
- `$DESIGN_TMPDIR/accepted-plan-findings.md` — If it exists and is non-empty, use it to identify decisions that reviewers challenged as suboptimal or that required plan revision.
- `$DESIGN_TMPDIR/contested-decisions.md` — Decisions that sketch agents disagreed on.
- `$DESIGN_TMPDIR/dialectic-resolutions.md` — How contested decisions were resolved.

## Behavior

Identify decisions in the implementation plan that meet any of these criteria:
1. **Not covered in Round 1** — decisions that emerged from the plan design, not from the original feature description.
2. **Challenged by reviewers** — decisions that appear in `accepted-plan-findings.md` (reviewers found them suboptimal and the plan was revised).
3. **Still contested** — decisions whose `dialectic-resolutions.md` entry matches any of the following (per the protocol in `${CLAUDE_PLUGIN_ROOT}/skills/shared/dialectic-protocol.md`):
   - `Disposition: voted` AND `Vote tally` shows a close 2-1 split (the minority 1 vote signals substantive disagreement).
   - `Disposition: fallback-to-synthesis` (the dialectic layer could not resolve).
   - `Disposition: bucket-skipped` (no debate occurred — tool was unavailable).
   - `Disposition: over-cap` (no debate occurred — decision ranked outside the top-5 dialectic cap).

Walk each uncovered branch one question at a time via sequential `AskUserQuestion` calls, providing a **recommended answer** for each question. If a question can be answered by exploring the codebase, do so and report the finding instead of asking the user.

Unlike Round 1, Round 2 MAY ask about architectural decisions and implementation approach — the sketch phase has already provided divergent perspectives, so anchoring is no longer a concern at this stage.

## Short-circuit

If all plan decisions are already covered by Round 1, no reviewer findings challenged them, and no decisions in `dialectic-resolutions.md` match the still-contested criteria above (no close 2-1 voted splits, no fallback-to-synthesis, no bucket-skipped, no over-cap entries), print `⏩ post-plan discussion — no additional decisions require discussion (<elapsed>)` and return to the calling Gate A prompt (re-fire the "ready for review / discuss more" `AskUserQuestion`). This body is invoked from Gate A's "Discuss more" branch on a post-plan re-entry — control returns to Gate A, NOT to Step 3b. Gate A's own exit decides where to go next ("Ready for review" on a post-plan re-entry proceeds to Step 3, not Step 3b).

## Output

The caller (Gate A) selects the target file: write resolved decisions to `$DESIGN_TMPDIR/discussion-round1.md` on first-time Gate A entry (when the body is invoked because Step 1d Round 1's main flow ran short), or to `$DESIGN_TMPDIR/discussion-round2.md` on post-plan Gate A re-entries (from Gate B(c) or Gate C(b)). Use the same Q&A format as Round 1:

```markdown
## Decision 1: <short title>
- **Question**: <the question asked>
- **Resolution**: <the answer — from user or codebase>
- **Source**: user / codebase
```

**Plan revision authority**: This sub-round body is invoked from Gate A on a re-entry path. The orchestrator MAY revise `$DESIGN_TMPDIR/plan.txt` to incorporate user-resolved decisions from this sub-round **directly**, because the user has explicitly engaged in the discussion and any plan change follows from their answers. After revising, re-run `ACTION=EMIT_PLAN` so `diff-lines.txt` reflects the new plan. Reviewer findings, however, are NEVER applied here — those are owned exclusively by Gate B's Apply all / per-finding Apply choices, regardless of how the discussion went. Print the revised plan only if substantive changes were made.

## Cap

At most **7 `AskUserQuestion` calls** in this step. If more than 7 decision branches remain, print: `⏩ Remaining design questions deferred to implementation.` and proceed.

## Terse answers

If the user gives a terse or non-responsive answer, accept the recommended answer and move on without re-asking.

Record `<N>` decisions resolved.
