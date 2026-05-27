# Design outline (Step 1d.7)

**Consumer**: `/design` Step **1d.7** — runs after Step **1d** Round 1 discussion and optional Step **1d.5** brainstorm, before Step **2a** sketches. Step **1e** Gate A is re-entry-only after a plan exists.

**Contract**: one-shot per invocation via `$DESIGN_TMPDIR/.outline-approved`. Produces `$DESIGN_TMPDIR/design-outline.md`; the outline is load-bearing for Step **2a** / Step **2b** feature-context substitution and plan drafting. It is never written to `composed-plan.md`, the `larch:plan` GitHub block, design-log publish bundles, or any `/implement`-consumed artifact.

**When to load**: only when Step **1d.7** executes — do not preload during Step 0 or Gate A re-entry.

**Binding convention**: single normative source for the outline gate, prompt loop, approval sentinel, cancel hygiene, and downstream consumption contract.

---

## Anti-halt override (Step 1d.7 only)

Step 1d.7 **overrides** the generic anti-halt continuation rule only for the narrow case: after printing the proposed design outline and the operator chooses **Refine outline**, the orchestrator may yield the turn for the free-form refinement reply.

**Hard prohibition (non-negotiable)**: Do **NOT** use `ScheduleWakeup`, wall-clock `sleep` polling loops, or Monitor-driven polling waits for operator replies. The refinement loop is operator-message driven.

---

## Entry guard

1. If `$DESIGN_TMPDIR/.outline-approved` exists: print `⏩ 1d.7: outline — skipped (already approved; .outline-approved present)` and **proceed to Step 2a**. Do not route to Gate A.
2. Otherwise print `> **🔶 /design 1d.7: outline**` and continue.

---

## Inputs

Read these artifacts before composing or refining the outline:

- `$DESIGN_TMPDIR/feature-description.txt` — always.
- `$DESIGN_TMPDIR/discussion-round1.md` — when present and non-empty.
- `$DESIGN_TMPDIR/brainstorm.md` — when present and non-empty.

The outline must be grounded in these inputs. Do not introduce speculative goals, scope, files, or implementation approaches that are not supported by the feature description, Round 1 decisions, or brainstorm synthesis.

---

## Outline schema

Write `$DESIGN_TMPDIR/design-outline.md` with this exact top-level structure. Keep it to short bullets only, about 15-25 total lines. No prose paragraphs.

```markdown
## Proposed Design Outline

### Goals
- 2-3 bullets

### Non-goals
- 2-3 bullets

### Approach sketch
- 3-5 bullets that name the direction: which surfaces, which gate, which file.
- This is not a fully-baked architecture. Step 2a sketches and Step 2a.5 dialectic explore concrete alternatives; the outline names the conceptual direction the operator has agreed to.

### Surfaces in scope
- File or directory names; conceptual surfaces, not full diff paths.

### Open questions
- 1-3 bullets, optional. Use `- None.` if there are no meaningful open questions.
```

---

## Output

1. Compose the outline in-session from the inputs above.
2. Write the complete file to `$DESIGN_TMPDIR/design-outline.md`.
3. Print the file contents to chat. The first line must be `## Proposed Design Outline`.

---

## Approval prompt

Fire `AskUserQuestion` after printing the outline:

- **Question**: `"Here is the proposed design direction. Approve and proceed to sketches + plan, refine the outline, or cancel?"`
- **Header**: `"Design outline"`
- **Options**:
  - **Approve outline** — write `$DESIGN_TMPDIR/.outline-approved` and **proceed to Step 2a**. The orchestrator MUST go to Step 2a, not Step 1e.
  - **Refine outline** — enter the Refine loop below.
  - **Cancel** — run Cancel hygiene below.

---

## Refine loop

When the operator chooses **Refine outline**:

1. Ask free-form: `"What would you like to refine? (Add ideas, remove items, adjust direction, narrow scope, etc.)"`
2. Receive the operator message as refinement instructions. Empty or non-actionable replies do not approve the outline; reprint it unchanged and re-fire the approval prompt.
3. Rewrite `$DESIGN_TMPDIR/design-outline.md` according to the refinement while preserving the five-section schema.
4. Reprint under `## Updated Design Outline` (changed sections only is acceptable; full reprint is simpler).
5. Re-fire the same Approve outline / Refine outline / Cancel prompt.

Loop until the operator explicitly chooses **Approve outline** or **Cancel** on the `AskUserQuestion`. Operator messages inside the free-form lane are refinement input, not implicit cancellation or approval.

---

## Cancel hygiene

On **Cancel**:

1. Export `SUMMARY_OUTCOME=cancelled-outline`.
2. Execute the `### Final summary block` fenced bash block from `SKILL.md` Step 0b. Do **not** call `render-final-summary.sh` directly from prompt-side orchestration.
3. Print `**ℹ /design cancelled by operator (outline gate).**`.
4. Exit 0. `$DESIGN_TMPDIR` is preserved because `PLAN_WRITE_OK=true` is not set on this path.

---

## Downstream consumer contract (additive)

- **Step 2a**: When substituting `<FEATURE_DESCRIPTION>` into sketch prompts, if `design-outline.md` exists and is non-empty, prepend a concise `## Approved direction (outline)` section to the feature text inside the substitution string. Do not replace the issue body file. Stack this with the brainstorm digest when both exist.
- **Step 2a.5**: Dialectic synthesis MAY incorporate the outline as binding direction context, treated like Round 1 user-resolved decisions rather than optional ideation.
- **Step 2b**: Read `design-outline.md` when present. Honor approved Goals, Non-goals, and Surfaces as binding scope. Let Approach sketch inform plan structure without locking in specific architecture choices; sketches and dialectic own architecture.
- **Step 3**: `plan-review-loop.sh` MAY merge non-empty `design-outline.md` into the feature-context file passed to reviewers alongside `brainstorm.md`. For L1, Step 2a and Step 2b consumption is sufficient because reviewers see the resulting plan that reflects the approved outline.

---

## Never-written-to-GitHub invariant

`$DESIGN_TMPDIR/design-outline.md` is session-internal. It is NOT included in `composed-plan.md`, the `larch:plan` issue-body block, the design-log publish bundle under `larch-logs/design/<RUN_ID>/`, or any artifact consumed by `/implement`.
