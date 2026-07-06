## Proposed Design Outline

### Goals
- Add a mandatory main-agent audit of accepted plan-review findings at Gate C Presentation, before the prompt, mirroring the architectural-guidelines assessment.
- Catch bad acceptance and bad application (unrelated plan damage) before the plan ships, since cost-reduced subtask agents apply findings via whole-file rewrites checked only mechanically.
- Under `--skip-approve`, make strong disagreement the tripwire that forces the Gate C prompt for unattended runs.

### Non-goals
- No per-round main-agent participation and no durable per-round diff emission in the background Step 3 loop.
- No raising the reviser tier in `plan revise-waterfall` (complementary lever, explicit OOS).
- No silent main-agent veto or auto-revert. Escalation only, through the existing Discuss-further to Gate A path.

### Approach sketch
- Preserve ONE durable snapshot of the plan as it enters the review pass (first-time and re-entry), surviving the mid-loop cleanup, so Gate C can diff it against the final `plan.txt`.
- Add a Gate C Presentation audit sub-step: read `accepted-plan-findings-all.md`, the on-disk `plan.txt`, and the snapshot; classify each accepted finding agree / mild-disagree / strong-disagree.
- Compose the audit digest prompt-side; add one persist helper (like `persist-design-assessment`) to write it into the design log.
- Strong disagreement surfaces as dissent in the Gate C `AskUserQuestion` and overrides `--skip-approve` auto-approve.

### Surfaces in scope
- `skills/design/references/approval-gates.md`: Gate C Presentation and the `--skip-approve` carve-out.
- `python/` review/design helper: preserve the pre-review snapshot, persist the audit assessment; `python/cli.py` verb wiring.
- Step 3 loop entry (`plan_review*.py`): minimal touch to write the one durable snapshot.
- Tests for the new helper(s).

### Open questions
- None.
