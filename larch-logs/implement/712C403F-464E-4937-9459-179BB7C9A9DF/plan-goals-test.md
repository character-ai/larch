## Goal
Implement issue #5209: [IMPLEMENTING] [BUG] /design halts after Gate C Approve instead of immediately continuing to Step 5b.

## Implementation Plan
## Summary

After the Gate C `AskUserQuestion` returns "Approve final design", the `/design` orchestrator ends the turn instead of immediately proceeding to Step 5b (OOS filing). The user must send a follow-up message ("continue") to unblock the run. This is an anti-halt violation: Gate C approval is not terminal, and Steps 5b through 6 must execute in the same turn.

## Original report

During a `/design 5152` run the orchestrator halted after Gate C returned "Approve final design". The user had to send "continue" to resume OOS filing (Step 5b), the architecture diagram (Step 5b.5), the plan write (Step 5c), and cleanup (Step 6). Root cause identified in conversation: the orchestrator treated the Gate C approval as a conversational endpoint and yielded the turn.

## Reproduction scenario

1. Run `/design <issue-number>` through to Gate C (Step 4b).
2. When `AskUserQuestion` presents the Gate C prompt, select **Approve final design**.
3. Observe: the orchestrator prints a brief confirmation and ends the turn without entering Step 5b.
4. The user must reply ("continue" or similar) before Steps 5b–6 execute.

Conditions that may increase the likelihood: large plan body triggering large-plan summary mode at Gate C; review-round cap reached (5/5) so the "Re-run review panel" option is omitted.

## Expected behavior

After `AskUserQuestion` at Gate C returns **Approve final design**, the orchestrator must immediately continue to Step 5b without yielding the turn. No user message should be required. `skills/design/SKILL.md` line ~778 states: "**Continue to Step 5 IMMEDIATELY** once Gate C returns Approve. Gate C is not terminal." `skills/design/references/approval-gates.md` line ~227 states: "When the user picks **Approve final design**, proceed to Step 5b."

## Observed behavior

The orchestrator ends the turn after Gate C approval. Step 5b (OOS filing), Step 5b.5 (architecture diagram), Step 5c (plan write / publish), and Step 6 (cleanup) run only after the user sends another message.

## Root cause analysis

`AskUserQuestion` is a user-facing interaction tool. When it returns an answer the model naturally treats that answer as the end of a user-assistant exchange and yields the turn. The existing directives — a blockquote at SKILL.md line 778 and a one-line "proceed to Step 5b" in `approval-gates.md` — are not strong enough to override this tendency. Specifically:

- The blockquote `> **Continue to Step 5 IMMEDIATELY**` appears before the Gate C question body in SKILL.md, not immediately after the `AskUserQuestion` result-handling prose. By the time the model processes the user's "Approve" answer, the pre-question directive has scrolled out of the immediate decision context.
- `approval-gates.md` § Loop exit (line 227) says "proceed to Step 5b" but contains no explicit anti-halt or do-NOT-end-the-turn directive.
- The global anti-halt reminder in SKILL.md mentions that Gate C(b) "Discuss further" re-entry and Gate C(c) "Re-run review panel" re-entry are NOT halts, but it does not explicitly list the **Approve** branch as a non-halt case. The omission leaves a gap for the model to classify approval as a natural conversation endpoint.

## Evidence

- `skills/design/SKILL.md` line 778: `> **Continue to Step 5 IMMEDIATELY** once Gate C returns Approve. Gate C is not terminal — finalize (OOS filing + plan write) and cleanup still must run.` (blockquote form; appears before, not after, the AskUserQuestion result handler).
- `skills/design/references/approval-gates.md` line 227: "When the user picks **Approve final design**, proceed to Step 5b." (no explicit anti-halt clause).
- Global anti-halt reminder in SKILL.md enumerates `4b→5` as a required step transition but does not explicitly say "Gate C Approve is NOT a halt" alongside the listed exceptions (Step 1d.5 and Step 1d.7 free-form lanes are explicitly named as narrow exceptions; Gate C Approve is not listed either way).
- Observed in run D53C42FC-CF7F-4281-AEA4-72B08C0F764E on issue #5152: user had to send "continue" after Gate C before OOS filing ran.

## Affected files

- `skills/design/SKILL.md` — Step 4b section (line ~778): anti-halt blockquote before the AskUserQuestion body.
- `skills/design/references/approval-gates.md` — Gate C § Loop exit (line ~227): no anti-halt directive on the Approve branch.

## Suggested fix(es)

**Option A — Add a mandatory breadcrumb print instruction directly after the AskUserQuestion result handler in `approval-gates.md`.**
After the "When the user picks **Approve final design**, proceed to Step 5b" sentence, add: "Immediately print `> **🔶 /design 5: finalize**` and continue to Step 5b without ending the turn." An explicit print instruction forces the model to emit output and continue rather than yield.

**Option B — Add an explicit Gate C Approve clause to the global anti-halt reminder.**
In the anti-halt reminder in SKILL.md, after listing the narrow exceptions (Step 1d.5 and Step 1d.7 free-form lanes), add: "Gate C **Approve final design** is NOT a halt; proceed to Step 5b immediately after `AskUserQuestion` returns that option."

**Option C — Strengthen the post-Gate-C directive in SKILL.md.**
Replace the blockquote form `> **Continue to Step 5 IMMEDIATELY**` with an inline bold directive placed AFTER the AskUserQuestion invocation prose (not before), to ensure it is read in the correct result-handling context.

The lowest-risk fix is Option A: adding a mandatory `> **🔶 /design 5: finalize**` breadcrumb print instruction to `approval-gates.md` § Loop exit directly after the Approve branch. This mirrors how other step-boundary transitions are enforced throughout the skill.

## Open questions

- Does the same halt occur when `--skip-approve` is used (auto-approval path)? The auto-approve path prints a breadcrumb and proceeds inline; the interactive path does not have an equivalent forced print.
- Does the same halt occur at Gate A "Ready for review" or Gate B "Apply all"? If so, the fix scope should extend to those gates as well.

## Test plan
(no test plan section in plan-file)
