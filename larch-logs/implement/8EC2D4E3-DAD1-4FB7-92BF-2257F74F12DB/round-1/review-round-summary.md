# Review Round 1

- Mode: `diff`
- 2 accepted, 1 rejected (0 neutral)

## Accepted Findings

### FINDING_1: implement/SKILL.md:447 still unconditionally loads execution-issues-tracking.md on Step 2.4 entry
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-dyn-implement-loads-output.txt
- **Severity**: important
- **Concern**: The plan requires loading `execution-issues-tracking.md` only when recording or triaging a pre-existing-code issue (dual-write / active OOS triage). Line 447 still has an unconditional `**MANDATORY — READ ENTIRE FILE**` at Step 2.4 entry before implementation. Every `STATUS=claude_fallback` run with zero pre-existing-code findings still pays a full policy read, contradicting the new reachability index (~323) and leaving the primary token-saving goal unmet on the hottest main-agent path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Remove upfront MANDATORY at 447; add conditional read immediately before first Pre-existing Code Issues log or oos-accepted-main-agent.md dual-write.
  - From codex-specialist-correctness-output.txt: Move the mandatory read to the actual pre-existing-code issue logging/triage path, or make this line conditional on an identified issue.
  - From cursor-specialist-edge-cases-output.txt: Remove the upfront MANDATORY at line 447; add a conditional MANDATORY read immediately before dual-write/triage actions, plus an explicit active-OOS-triage read if line 447 is deleted.
  - From codex-specialist-edge-cases-output.txt: Move the mandatory read into the actual pre-existing-code recording or triage branch, and let normal implementation proceed without loading it until that trigger exists.
  - From codex-specialist-testing-output.txt: Move the mandatory read into conditional prose that fires only when a Pre-existing Code Issue is identified, recorded, or triaged.
  - From dyn-dyn-implement-loads-output.txt: Move the line 447 directive inside the dual-write moment (for example, immediately before logging under `Pre-existing Code Issues` or appending to `oos-accepted-main-agent.md`), or gate it with an explicit prompt-side predicate such as "main agent has identified a pre-existing-code candidate." Keep self-review step 3 and Step 8 `oos-pipeline` reads as the other pinned sites.


### FINDING_2: design/SKILL.md Step 1d.5 skip routing is ambiguous and can break completion or conditioning
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-dyn-design-loads-output.txt
- **Severity**: important
- **Concern**: Step 1d.5 skip logic at ~365–375 is structurally fragile. Separate `If` branches (not a single `brainstorm_requested is not true OR .brainstorm-done exists` guard) each forward-reference a completion fence "below," while `step1d5 --mode complete` appears later under a unified skip block—risking (a) jump to 1d.7 without writing `.completed/step-1d.5`, or (b) double-running the completion fence. The `brainstorm_requested` guard is checked before `.brainstorm-done`, so `false` + sentinel-present yields a generic skip breadcrumb instead of the sentinel-specific message. Skip branches lack explicit "do not execute remaining Step 1d.5 body" language (unlike `brainstorm.md`), so a literal executor may still reach `Only when brainstorm_requested=true…` and force-load `brainstorm.md` on a skip path. The `.brainstorm-done` skip path has no Step 2a repair when `brainstorm_requested=true`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Check .brainstorm-done first or merge branches so sentinel-specific skip breadcrumb is preserved.
  - From dyn-dyn-design-loads-output.txt: Collapse to one mutually exclusive guard matching the plan (`not true` OR `.brainstorm-done` → skip breadcrumb; else read `brainstorm.md`), run `step1d5 --mode complete` exactly once, then continue to Step 1d.7. Remove the forward-reference "below" wording or duplicate completion block.
  - From dyn-dyn-design-loads-output.txt: Use explicit `else` / "on skip, do not read `brainstorm.md` or execute any remaining Step 1d.5 body" language, mirroring the entry-guard contract in `skills/design/references/brainstorm.md:25-30`.


