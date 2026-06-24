# Review Round 1

- Mode: `diff`
- 2 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Failure logging preamble contradicts loop-internal Consumer contract
- **Reviewer(s)**: cursor-specialist-correctness, dyn-dyn-plan-review-docs
- **Severity**: important
- **Concern**: The Consumer / When-to-load preamble marks collection, aggregation, ballot rebuild, voter dispatch, and tally as loop-internal to `python/plan_review.py`, but the **Failure logging** block (lines 3–24) still gives prompt-side orchestrator runbooks for `compose-collector-failure-log` and `run-log append-failure`. `python/plan_review_round.py` already logs collector failures on the driver path. A mandatory full-file read on Step 3 entry can lead the orchestrator to duplicate failure logging on recovery paths or fight the loop driver.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Compress Failure logging to a loop-internal pointer (mirror Collecting section) or relocate the contract to SKILL.md driver prose and remove orchestrator imperatives from plan-review.md.
  - From dyn-dyn-plan-review-docs: Compress **Failure logging** the same way as **Collecting External Reviewer Results**: one line stating it is loop-internal, with a pointer to `python/plan_review_round.py` (or drop the block entirely). Keep only orchestrator-relevant failure guidance if a genuine prompt-side path still exists.


### FINDING_5: Competition notice "owned by runtime renderer" claim is incorrect for plan-review
- **Reviewer(s)**: codex-specialist-edge-cases, dyn-dyn-plan-review-docs
- **Severity**: important
- **Concern**: Prose says the competition notice is owned by the runtime renderer, but `python/cli.py render plan-review` / `render_plan_review_main` does not emit it (only `render specialist --competition-notice` does, for code review). Plan-review panel dispatch calls `render plan-review` without that flag. Fallback Claude reviewers use the `code-reviewer` Agent archetype, not the plan-review renderer. The removed "append Competition notice blockquote" instruction was already dead in loop mode; the replacement prose is factually wrong and may send maintainers to add competition notice to the wrong render path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Add the notice to render_plan_review_main with tests, or document that the notice is intentionally retired for plan-review prompts.
  - From dyn-dyn-plan-review-docs: Reword line 95 to state plan-review reviewers do not receive a competition notice (or point explicitly to `render specialist --competition-notice` as a code-review-only surface). Drop the claim that the plan-review runtime renderer owns that text.


