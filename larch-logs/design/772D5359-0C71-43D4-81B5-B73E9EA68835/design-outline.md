## Proposed Design Outline

### Goals
- Stop /design Step 4 from labeling already-addressed reviewer concerns as "Unimplemented" gaps. Use a deterministic report relabel plus annotation.
- Cut redundant re-raised findings at the source via a reviewer-prompt instruction to check the current plan first.
- Remove the stale pre-launch `📊 Reviewers:` breadcrumb. Keep the post-notification real-status table.

### Non-goals
- No semantic or LLM suppression of rejected findings. No heuristic that could drop genuine gaps.
- No change to on-disk `rejected-findings.md` (audit fidelity preserved).
- No change to review continuation, round-cap, or churn dynamics (#4808 umbrella).

### Approach sketch
- #4884 report: relabel the SKILL.md Step 4 heading and add a one-line "considered, not adopted" framing, so entries no longer read as gaps.
- #4884 source: add a "verify the concern is not already addressed in the current plan before raising it" instruction to the reviewer prompt; confirm reviewers get the latest plan.txt each round.
- #4838 breadcrumb: drop the pre-launch all-pending print from the SKILL.md "Compact reviewer status table" section and the Step 3 wait rules; keep the post-notification print.
- Audit /implement and shared/progress-reporting.md for the same pre-launch static pattern; remove clearly-stale ones, defer ambiguous ones to OOS.
- Add regression coverage in python/test_plan_review.py.

### Surfaces in scope
- `python/plan_review.py` (rejected-findings emit; reviewer-prompt render path)
- `skills/design/SKILL.md` (Step 4 heading; "Compact reviewer status table" and Step 3 wait rules)
- `skills/design/scripts/design-step3b-tail.sh` and `.md` (rejected-body emit wrapper)
- reviewer-prompt template (`python/cli.py render plan-review`, `references/plan-review.md`)
- `skills/implement/SKILL.md` and `skills/shared/progress-reporting.md` (breadcrumb audit)
- `python/test_plan_review.py` (regression coverage)

### Open questions
- Exact relabel wording, and whether annotation is a section preamble or a per-entry note. Prose detail resolved during drafting.
