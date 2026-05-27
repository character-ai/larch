# Design outline (Step 1d.7)

**Consumer**: `/design` Step **1d.7** — runs after Step **1d** Round 1 discussion and optional Step **1d.5** brainstorm, before Step **2a** sketches, on runs that continue from Round 1 into new plan production. The already-planned ad-hoc Q&A-only branch does **not** invoke this file. Step **1e** Gate A is re-entry-only after a plan exists.

**Contract**: one-shot per invocation via `$DESIGN_TMPDIR/.outline-approved`. Produces `$DESIGN_TMPDIR/design-outline.md`; the outline is load-bearing for Step **2a** / Step **2a.5** / Step **2b** only when the file is non-empty **and** `$DESIGN_TMPDIR/.outline-approved` exists. It is never written to `composed-plan.md`, the `larch:plan` GitHub block, or any `/implement`-consumed artifact. Session-log publishing may still capture the file as a top-level artifact through redaction, so do **not** treat it as excluded from design-log publish bundles.

**When to load**: only when Step **1d.7** executes — do not preload during Step 0 or Gate A re-entry.

**Binding convention**: single normative source for the outline gate, prompt loop, approval sentinel, cancel hygiene, and downstream consumption contract.

---

## Anti-halt override (Step 1d.7 only)

Step 1d.7 **overrides** the generic anti-halt continuation rule only for the narrow case: after printing the proposed design outline and the operator chooses **Refine outline**, the orchestrator may yield the turn for the free-form refinement reply.

**Hard prohibition (non-negotiable)**: Do **NOT** use `ScheduleWakeup`, wall-clock `sleep` polling loops, or Monitor-driven polling waits for operator replies. The refinement loop is operator-message driven.

---

## Entry guard

1. If `$DESIGN_TMPDIR/.outline-approved` exists **and** `$DESIGN_TMPDIR/plan.txt` does **not** exist: print `⏩ 1d.7: outline — skipped (already approved; .outline-approved present)` and **proceed to Step 2a**. Do not route to Gate A.
2. If `$DESIGN_TMPDIR/.outline-approved` exists **and** `$DESIGN_TMPDIR/plan.txt` exists: print `⏩ 1d.7: outline — skipped (approved outline + existing plan; stay on post-plan path)` and continue on the existing post-plan gate path. This is stale-sentinel / resumed-session recovery; do **not** re-enter Step 2a sketches once a plan already exists.
3. Otherwise print `> **🔶 /design 1d.7: outline**` and continue.

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
  - **Approve outline** — write `$DESIGN_TMPDIR/.outline-approved`, print `✅ 1d.7: outline approved — proceeding to sketches`, and **proceed to Step 2a**. The orchestrator MUST go to Step 2a, not Step 1e. This sentinel is written **only** on explicit Approve.
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

Loop until the operator explicitly chooses **Approve outline** or **Cancel** on the `AskUserQuestion`. Operator messages inside the free-form lane are refinement input, not implicit cancellation or approval. **Refine outline** does **not** write `$DESIGN_TMPDIR/.outline-approved`.

---

## Cancel hygiene

On **Cancel**:

1. Export `SUMMARY_OUTCOME=cancelled-outline`.
2. Execute the `### Final summary block` fenced bash block from `SKILL.md` Step 0b. Do **not** call `render-final-summary.sh` directly from prompt-side orchestration.
3. Print `**ℹ /design cancelled by operator (outline gate).**`.
4. Exit 0. `$DESIGN_TMPDIR` is preserved because `PLAN_WRITE_OK=true` is not set on this path. **Cancel** does **not** write `$DESIGN_TMPDIR/.outline-approved`.

---

## Downstream consumer contract (additive)

- **Step 2a**: When substituting `<FEATURE_DESCRIPTION>` into sketch prompts, prepend a concise `## Approved direction (outline)` section only when `design-outline.md` exists, is non-empty, **and** `$DESIGN_TMPDIR/.outline-approved` exists. Do not replace the issue body file. Stack this with the brainstorm digest when both exist.
- **Step 2a.5**: Dialectic synthesis MAY incorporate the outline as binding direction context only when the same approved-outline conditions hold (`design-outline.md` non-empty + `.outline-approved` present), treated like Round 1 user-resolved decisions rather than optional ideation.
- **Step 2b**: Read `design-outline.md` only when it is present, non-empty, **and** `$DESIGN_TMPDIR/.outline-approved` exists. Honor approved Goals, Non-goals, and Surfaces as binding scope. Let Approach sketch inform plan structure without locking in specific architecture choices; sketches and dialectic own architecture.
- **Step 3**: `plan-review-loop.sh` MAY merge `design-outline.md` into the feature-context file passed to reviewers alongside `brainstorm.md` only when the approved-outline conditions hold. For L1, Step 2a and Step 2b consumption is sufficient because reviewers see the resulting plan that reflects the approved outline.

---

## Never-written-to-GitHub invariant

`$DESIGN_TMPDIR/design-outline.md` is session-internal with respect to the implementation handoff. It is NOT included in `composed-plan.md`, the `larch:plan` issue-body block, or any artifact consumed by `/implement`. Design-log publishing may still capture the file in the redacted session bundle under `larch-logs/design/<RUN_ID>/`, so do not rely on bundle exclusion as a secrecy boundary.
