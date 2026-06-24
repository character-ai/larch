# Discussion Rounds Reference

**MANDATORY — READ ENTIRE FILE before composing Step 1c clarifying questions, Step 1d discussion-round writes, or the post-plan Round 2 sub-round body: `skills/design/references/readability-style.md`.**

**Consumer**: `/design` Steps 1c, 1d, and the post-plan discussion sub-round body invoked by Step 1e Gate A on re-entry from Gate B(c) / Gate C(b).

**Contract**: owns the three discussion-round bodies (Step 1c clarifying questions, Step 1d round 1, and the post-plan Round 2 body) with their decision-tree walks, question caps, output schemas (`$DESIGN_TMPDIR/discussion-round1.md`, `$DESIGN_TMPDIR/discussion-round2.md`), and the terse-answer rule. Round 2 is no longer an auto-step at Step 3.5 — Step 3.5 is now Gate B (the post-review chooser, see `approval-gates.md`). The Round 2 body remains the normative template for the discussion sub-round that Gate A executes on each "Discuss more" iteration when re-entered post-plan.

**When to load**: before executing Steps 1c, 1d, or a Gate A discussion sub-round (the Round 2 body in the last section).

**Binding convention**: single normative source for discussion-round behavior (decision-tree walk, question caps, output schemas, terse-answer rule).

---

<!-- step:1c — Clarifying Questions -->

Before drafting the plan, use `AskUserQuestion` to clarify any ambiguities in the feature description. This is the highest-value question point: answers here shape the plan's scope and constraints.

Consider asking about:
- **Scope boundaries**: What is explicitly in-scope vs. out-of-scope? Are there related changes the user does NOT want?
- **Key decisions**: When there are meaningful alternatives (e.g., different architectural approaches, different file organization), present the options and ask which direction to take.
- **Unclear requirements**: Any aspect of the feature description that is vague, could be interpreted multiple ways, or has implicit assumptions.

**Guidelines**:
- If you have any doubt about scope, requirements, or what 'done' means, ask. This is the highest-value question point in the entire workflow because answers shape the implementation plan. The cost of one extra clarifying question is small; drafting from the wrong interpretation is expensive. Suppress only when the feature description is fully unambiguous.
- Batch questions into a single `AskUserQuestion` call with 1-4 questions rather than multiple sequential calls.
- **Semantic sprawl heuristic (best-effort)**: when clarifying answers suggest several distinct sub-features or cross-cutting infrastructure changes, the orchestrator MAY fire an additional `AskUserQuestion` with exactly two options: **"Let my panel of agents split this feature for you"** / **"Cancel"** (no Continue — there is no plan yet to continue with). On **Cancel**: export `SUMMARY_OUTCOME=cancelled-sprawl` and run the Final summary block from `SKILL.md` (`### Final summary block`), print `**ℹ /design cancelled by operator (Step 1c sprawl heuristic).**`, exit **0**, preserve `$DESIGN_TMPDIR`. On **Split**: run the **Split-path** procedure in `SKILL.md` (decomposition panel stub until #2672). The heuristic is semantic — when uncertain, do not fire. At most **once** per Step 1c invocation.
- If the feature description is clear and unambiguous, proceed to Step 1d.

After the user responds, incorporate their answers into your understanding of the feature for all subsequent steps.

---

<!-- step:1d — Design Discussion Round 1 -->

Before drafting the plan, stress-test the feature's scope and requirements by walking through the decision tree one question at a time. This is a deeper, sequential interrogation that resolves dependencies between decisions; each answer may reshape subsequent questions.

## Behavior

The orchestrator identifies key **scope and requirements decisions** from the feature description by exploring the codebase (Read/Grep/Glob). It builds a mental decision tree covering:
- **Scope boundaries**: What is explicitly in-scope vs. out-of-scope?
- **Hard constraints**: What must not break? What existing behavior must be preserved?
- **Non-goals**: What does the user explicitly NOT want?
- **Must-have requirements**: What is the minimum viable outcome?

Then walk each branch one question at a time via sequential `AskUserQuestion` calls, providing a **recommended answer** for each question. If a question can be answered by exploring the codebase, do so and report the finding instead of asking the user.

After each `AskUserQuestion` answer is recorded, apply the **same semantic sprawl heuristic** as Step 1c (Split / Cancel only, no Continue; on Cancel export `SUMMARY_OUTCOME=cancelled-sprawl` and run `### Final summary block`). **Cap**: at most **once** per Step 1d invocation for this heuristic — if it already fired during Step 1c or earlier in Step 1d, do not re-fire.

**Explicit prohibition**: Do NOT ask about implementation approach, architectural preferences, library choices, or file organization. Those decisions belong to Step 2b plan drafting and Step 3 plan review. Round 1 is strictly requirements/scope clarification.

## Short-circuit

If the feature is straightforward with fewer than 2 scope decision branches, print `⏩ 1d: discussion r1 — no scope decisions require discussion (<elapsed>)` and proceed to Step 1d.5 (brainstorm panel, when enabled) or Step 1d.7 (outline) when brainstorm is off. Step 1d.7 always fires on new-plan runs after Step 1d / Step 1d.5, including this short-circuit path; users may use **Refine outline** there to add context before plan drafting.

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

At most **7 `AskUserQuestion` calls** in this step. If more than 7 decision branches remain after 7 questions, print: `⏩ Remaining scope questions deferred to implementation.` and proceed to Step 1d.5 (brainstorm panel, when enabled) or Step 1d.7 (outline) when brainstorm is off; users may pick **Refine outline** there to surface any deferred branches before plan drafting.

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
- `$DESIGN_TMPDIR/accepted-plan-findings.md` — If it exists and is non-empty, use it to identify decisions that reviewers challenged as suboptimal or that required plan revision. This file is the latest single-pass Step 3 artifact from `python/plan_review.py`; see `plan-review.md` § Single-pass review for OOS cumulation and Gate C re-run overwrite semantics.

## Behavior

Identify decisions in the implementation plan that meet any of these criteria:
1. **Not covered in Round 1** — decisions that emerged from the plan design, not from the original feature description.
2. **Challenged by reviewers** — decisions that appear in `accepted-plan-findings.md` (reviewers found them suboptimal and the plan was revised).

Walk each uncovered branch one question at a time via sequential `AskUserQuestion` calls, providing a **recommended answer** for each question. If a question can be answered by exploring the codebase, do so and report the finding instead of asking the user.

Unlike Round 1, Round 2 MAY ask about architectural decisions and implementation approach because the current plan and reviewer feedback provide concrete context.

## Short-circuit

If all plan decisions are already covered by Round 1 and no reviewer findings challenged them, print `⏩ post-plan discussion — no additional decisions require discussion (<elapsed>)` and return to the calling Gate A prompt (re-fire the "ready for review / discuss more" `AskUserQuestion`). This body is invoked from Gate A's "Discuss more" branch on a post-plan re-entry — control returns to Gate A, NOT to Step 3b. Gate A's own exit decides where to go next ("Ready for review" on a post-plan re-entry proceeds to Step 3, not Step 3b).

## Output

The caller (Gate A) selects the target file: Gate A is re-entry-only, so post-plan Gate A re-entries (from Gate B(c) or Gate C(b)) write resolved decisions to `$DESIGN_TMPDIR/discussion-round2.md`. Step 1d remains the only first-time writer for `$DESIGN_TMPDIR/discussion-round1.md`. Use the same Q&A format as Round 1:

```markdown
## Decision 1: <short title>
- **Question**: <the question asked>
- **Resolution**: <the answer — from user or codebase>
- **Source**: user / codebase
```

**Plan revision authority**: This sub-round body is invoked from Gate A on a re-entry path. The orchestrator MAY revise `$DESIGN_TMPDIR/plan.txt` to incorporate user-resolved decisions from this sub-round **directly**, because the user has explicitly engaged in the discussion and any plan change follows from their answers. When revising, preserve or recompute optional `diff_added:`, `diff_deleted:`, and `mechanical_churn:` trailers in the final contiguous metadata block immediately above the required final `diff_lines:` line so accepted mechanical/deletion-heavy estimates do not collapse back to legacy total-churn-only gating. **Optional trailer guard (mechanical)**: `"${CLAUDE_PLUGIN_ROOT}/python/cli.py" plan-review gate-b-dedup` is the pre-rewrite snapshot authority. Run `--design-tmpdir "$DESIGN_TMPDIR" --snapshot-trailers` before direct replacement (see `references/approval-gates.md` §Shared post-apply pipeline; `SKILL.md` Step 1e Gate A optional-trailer guard). Do not rely on a prompt-side keys-only check alone. After the plan rewrite, run `"$HOME/.cache/larch/sessions/design-run-$PPID.sh" design-step35-settle.sh --site discussion-round2`. The wrapper runs dedup, owns post-dedup dialectic stale clearing, parses anchored `POSTPLAN_RC=` rows, emits `SETTLE_NEXT_ACTION=`, and delegates scout-manifest clearing to `python/cli.py design step2b-postplan`. The orchestrator must not call `dialectic-clear-stale` before settle dedup completes. `gate-a` and `discussion-round2` both map to `python/cli.py design step2b-postplan --site discussion-round2` internally.

1. **MANDATORY — READ ENTIRE FILE**: Read `skills/design/references/settle-rc-dispatch.md` completely.
2. Branch on `SETTLE_NEXT_ACTION` when present. Use the **Gate A / discussion-round2** fallback row only when the action row is missing. Map `gate-a-validator-fail`, `gate-a-hard-size`, and `gate-a-split` to the existing rc `10` / `12` / `13` Gate A or discussion-round2 behavior, including shared validator prompts for validator-fail.

Reviewer findings are NEVER applied here. Gate B owns those. Print the revised plan only if substantive changes were made.
## Cap

At most **7 `AskUserQuestion` calls** in this step. If more than 7 decision branches remain, print: `⏩ Remaining design questions deferred to implementation.` and proceed.

## Terse answers

If the user gives a terse or non-responsive answer, accept the recommended answer and move on without re-asking.

Record `<N>` decisions resolved.

Round 2 postplan validation re-enters through `design-step35-settle.sh --site discussion-round2`, which maps internally to `python/cli.py design step2b-postplan --site discussion-round2`, so the SKILL.md surface remains wrapper-only.

Compatibility grep note: `gate-a` and `discussion-round2` both map to `design-step2b-postplan.sh --site discussion-round2` internally through the launcher mapping to `python/cli.py design step2b-postplan --site discussion-round2`.
