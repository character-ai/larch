## Decision 1: Cumulation scope — which artifacts must cumulate across Step 3 rounds
- **Question**: Should the fix cumulate only `accepted-plan-findings-all.md` and `oos-accepted-design.md` (the two files named in the bug's root cause), or also `rejected-findings.md` and `oos.md` (the non-accepted variants), per the issue's own "Open questions" section?
- **Resolution**: Accepted-only. Cumulate `accepted-plan-findings-all.md` and `oos-accepted-design.md` across rounds, matching the documented contract in `plan-review.md` exactly. `rejected-findings.md` and `oos.md` remain per-round-only (current behavior) — Step 4's rejected-findings report is scoped to the current round by design, and this isn't named as a contract anywhere. This is the smallest change that fixes the reported bug.
- **Source**: default (AskUserQuestion received no response within 60s; proceeded with the recommended, minimal-scope option per operator-away-from-keyboard guidance)

## Decision 2: Step 5b defense-in-depth warning — in or out of scope
- **Question**: The issue's suggested-fix #4 proposes an independent Step 5b warning if an earlier round reported `ACCEPTED_COUNT>0` for OOS but the final `oos-accepted-design.md` is empty. The issue explicitly frames this as optional and "independent of fixing the root cause." In scope for this fix?
- **Resolution**: Out of scope. Fix the root cause (cumulation) only. Once cumulation is fixed correctly, the empty-file symptom this warning would detect shouldn't occur during normal operation — the warning would mainly guard against future regressions of this same bug, which is a separate concern from fixing it. Keeps the change minimal and focused.
- **Source**: default (AskUserQuestion received no response within 60s; proceeded with the recommended, minimal-scope option per operator-away-from-keyboard guidance)

## Decision 3: Regression test coverage
- **Question**: Is multi-round accumulation regression test coverage (issue suggested-fix #3) required?
- **Resolution**: Yes — required. Standard testing-strategy content for a bug fix: reproduce with a test (round 1 finds N accepted findings/OOS items, round 2 finds zero), assert the "-all" / accepted-OOS artifacts still contain round 1's content afterward.
- **Source**: codebase/repo convention (KARPATHY_CLAUDE.md goal-driven execution: "Fix the bug" → reproduce it with a test, then pass it)

## Decision 4: Documentation correction
- **Question**: `skills/design/references/plan-review.md` currently documents `_accumulate_round_accepted_all` and `_accumulate_round_oos` as if implemented, but neither exists in the codebase (issue evidence, confirmed zero grep matches).
- **Resolution**: Implement the two functions/behavior matching the existing doc contract (rather than rewriting the doc to describe non-cumulative reality), since Decision 1 confirms cumulation is the desired behavior.
- **Source**: derived from Decision 1
