## Goal
Implement issue #5241: [IMPLEMENTING] [BUG] /design and /implement orchestrators must not probe or generate turns on premature empty task-notifications from background review.

## Implementation Plan
## Summary

The `/design` orchestrator is specified to run one foreground sentinel probe per `<task-notification>` during the Step 3 review wait, even when the notification carries empty task output. Combined with companion bug #5240 (review process fires dozens of spurious notifications), this results in 50+ wasted response turns (and proportional token cost) per design run. The `/implement` orchestrator already documents the correct behavior: end the turn on premature empty notifications with no tool calls. The `/design` Step 3 and Step 5c recovery protocols must be updated to match.

## Original report

Both /design and /implement orchestrators generate response turns (consuming model tokens) for every premature empty task-notification fired by the background review process. The correct behavior is to end the turn silently when the notification carries no meaningful output (empty task output) and the terminal sentinel is absent. The /implement SKILL.md already documents this correctly ("when a task-notification fires prematurely with empty stdout on an /implement long-running fence, end the turn and wait for the next task-notification"). The /design SKILL.md adds a "one foreground probe per recovery turn" protocol (#4489, #4725) that turns each spurious notification into a wasted probe turn. Since the review process fires dozens of spurious notifications (see companion bug #5240), this results in 50+ wasted orchestrator turns per design run. Both orchestrators must be updated to NOT generate tool-call-bearing response turns in response to premature empty notifications. The sentinel probe should be deferred until there is positive evidence the review has finished (non-empty task output, elapsed time heuristic, or user instruction) rather than running unconditionally on every empty notification. The /design "may confirm completion" language in the Step 3 recovery protocol should be changed to explicitly say: if task output is empty and the sentinel is absent, end the turn immediately with no tool calls. This matches the /implement contract and eliminates the O(notifications) token waste.

## Reproduction scenario

1. Run `/design <any issue>`.
2. After the Step 3 background review launch, observe the repeated `<task-notification>` events (see bug #5240 for root cause).
3. Observe: on each notification, the `/design` orchestrator calls a Bash probe (`[ -f .completed/step-3-terminal ]`), sees WAIT, and then ends the turn.
4. Expected: the orchestrator ends the turn on premature empty notifications with zero tool calls.
5. Cost: at 50+ notifications per run, the probe-per-notification contract costs hundreds of extra turns and thousands of extra tokens.

Note: `/implement` is unaffected because its SKILL.md NEVER #8 explicitly says "end the turn" on premature empty notifications without probing. `/design` has a divergent protocol.

## Expected behavior

- When a `<task-notification>` fires and the task output is empty, the orchestrator should end the turn immediately with no tool calls.
- Only react to notifications that carry non-empty task output (which indicates the bash script has actually written its completion output).
- The sentinel probe (`[ -f .completed/step-3-terminal ]`) should run only when there is positive evidence of completion (non-empty task output), not on every notification.
- This matches the `/implement` contract: "end the turn and wait for the next `<task-notification>`" on empty notifications.

## Observed behavior

- Each `<task-notification>` triggers one foreground Bash probe per the `/design` SKILL.md contract ("after a premature empty notification, run at most one non-sleeping `[ -f … ]` or `test -f …` probe per recovery turn").
- With 50+ spurious notifications from bug #5240, this becomes 50+ probe turns.
- Each probe turn costs ~150–200 tokens (model response + tool call overhead).
- Total waste: ~7,500–10,000 tokens per design run, plus the latency of 50+ interaction turns.

## Root cause analysis

The `/design` SKILL.md Step 3 recovery protocol was added in #4489 and #4725 to detect completion faster than waiting for the final notification. The intent was good: probe the sentinel so that if the review finishes between notifications, the orchestrator detects it immediately rather than waiting for another event.

However, combined with bug #5240 (spurious notifications from bash job-control output), the probe-per-notification contract produces O(notifications) turns instead of O(1). The protocol assumes notifications are rare and each one is likely meaningful; the actual platform behavior fires one per subprocess exit during the review.

The `/implement` SKILL.md already arrived at the correct steady-state: don't probe on empty notifications, just end the turn and wait for the actual completion notification (which carries non-empty task output from the normalize-status step). The `/design` SKILL.md diverged from this by adding the probe step.

**Secondary observation**: the `/design` SKILL.md language "one foreground probe **may** confirm completion" uses permissive "may" but practitioners treat it as mandatory. Changing it to match `/implement`'s explicit "end the turn" wording would prevent future recurrence.

## Evidence

- `skills/design/SKILL.md` Anti-pattern #4 (line ~195 in the distributed copy): "after a premature empty notification, run at most one non-sleeping `[ -f … ]` or `test -f …` probe per recovery turn against `.completed/step-3-terminal`" — mandates probe on every notification.
- `skills/design/SKILL.md` Step 3 immediate-background wait rule (line ~594): "after a premature empty notification, one foreground probe of `.completed/step-3-terminal` per recovery turn may confirm envelope durability" — same directive, permissive phrasing.
- `skills/implement/SKILL.md` NEVER #8: "When a `<task-notification>` fires prematurely with empty stdout on an `/implement` long-running fence, **end the turn** and wait for the next `<task-notification>`; do not probe" — the correct contract.
- Observed in a recent `/design 5156` run: 50+ consecutive `<task-notification>` events, each producing a Bash probe turn with WAIT result, before the actual review completion.
- Companion bug: #5240 (fix the source of spurious notifications).

## Affected files

- `skills/design/SKILL.md` — Anti-pattern #4 and Step 3 "Immediate-background wait rule" both specify the probe-per-notification contract; both need updating.
- `skills/design/SKILL.md` — Step 5c "Immediate-background wait rule" has the same structure (`one foreground probe of .completed/step-5c-terminal per recovery turn`); update in the same pass for consistency.
- `skills/design/SKILL.md` — `### Final summary block` section also references `one foreground probe of .completed/step-final-summary per recovery turn`; update for consistency.
- `skills/implement/SKILL.md` — Already has correct wording; serves as the reference model for the fix.

## Suggested fix(es)

**Primary fix (SKILL.md language)**: In `skills/design/SKILL.md`, replace the Step 3 premature-notification recovery rule in Anti-pattern #4 and the Step 3 "Immediate-background wait rule" with the `/implement` contract:

Before:
> "After a premature empty notification, run at most one non-sleeping `[ -f … ]` or `test -f …` probe per recovery turn against `.completed/step-3-terminal`"

After:
> "When a `<task-notification>` fires prematurely with empty task output, end the turn immediately with no tool calls and wait for the next `<task-notification>`."

Apply the same change to Step 5c and the Final summary block fence for consistency.

**Optional enhancement**: add a positive-signal condition. Before deciding whether to probe, check if the task output file is non-empty. Non-empty output indicates the bash script has written its normalize-status output (real completion). Empty output indicates a spurious flush (no probe needed):

> "After `<task-notification>`: check if the task output file is non-empty. If non-empty, probe `.completed/step-3-terminal`. If empty, end the turn with no tool calls."

This two-condition approach detects completion at the earliest notification that carries actual output, while avoiding all spurious probe turns. It would also resolve the risk that fixing the wording alone causes missed completions if the platform ever delivers real completions with non-trivial delay.

Note: this fix is additive to bug #5240. Even if the source of spurious notifications is fixed, the probe-per-notification contract is fragile and should be aligned with `/implement` regardless.

## Open questions

- Should the "probe only on non-empty output" enhancement be part of this fix, or is language-only sufficient once #5240 is fixed?
- Are Step 5c and Final summary block fences subject to the same spurious-notification problem as Step 3, or is it only Step 3 that has the bash job-control output issue?
- Should `hook-bg-poll-guard.sh` be extended to deny probe Bash fences when the task output is empty (as a mechanical enforcement of the new contract)?

## Test plan
(no test plan section in plan-file)
