## Goal
Implement issue #4598: [IMPLEMENTING] [OOS] Aggregated rollup of 2 capped OOS items.

## Implementation Plan
## Plan

Make the minimum docs-only patch.

- Align `docs/skills.md` `/status` catalog text with `skills/status/SKILL.md`.
- Align `docs/external-reviewers.md` degraded-tools gate text with `skills/shared/external-reviewers.md`.
- Do not change skill prompts, shared contracts, scripts, or tests.

## Files to modify/create

### UPDATED: docs/skills.md

Replace the stale `/status` sentence that says degraded status may mean "reduced panel or Claude-only fallback".

Use the current status skill contract instead:

- one unavailable vendor: `/implement` requires explicit operator confirmation, then continues with that vendor dropped from the reduced panel.
- both unavailable vendors: `/implement` hard-fails until at least one vendor is fixed.

### UPDATED: docs/external-reviewers.md

Replace the stale degraded-tools gate paragraph in `## Availability Checks`.

Keep the existing scope and structure, but fix the routing:

- Healthy: proceed silently.
- One vendor down, no Continue sentinel: show the explanation and require Continue or Abort in interactive mode; in non-interactive, CI, eval, autonomous-loop, and `/review --subagent` contexts, emit a prompt-required envelope instead of auto-proceeding.
- One vendor down, Continue sentinel present (`.degraded-tools-gate-prompted`): proceed degraded in every mode, including non-interactive resume after a prior operator chose Continue.
- Both vendors down: hard-fail in every mode, ignore stale sentinels, and do not ask Continue or Abort.
- Preserve the statement that the gate reports `binary-missing` vs `runtime-probe-failed`.

## Edge cases

- Avoid saying "Claude-only fallback" for Step 0 degraded-tools gating. The current contract hard-fails when both vendors are down.
- Do not imply the gate controls later reviewer routing. `skills/shared/external-reviewers.md` says Step 0 probe health is not a later routing input.
- Do not describe non-interactive one-down runs without a sentinel as auto-proceeding. They need prompt-required routing.
- Do not collapse one-down into a single non-interactive rule that omits the Continue-sentinel exception. A resume with `.degraded-tools-gate-prompted` must proceed degraded even in non-interactive contexts.

## Failure modes

- If the docs mention both-down prompting, the docs will conflict with the hard-fail contract.
- If the docs say one-down auto-proceeds without a sentinel, operators may miss the required explicit Continue path.
- If non-interactive wording ignores `.degraded-tools-gate-prompted`, resumed runs may incorrectly emit prompt-required envelopes after an operator already chose Continue.
- If the docs describe Claude fallback as a Step 0 degraded state, they may confuse Step 0 gate behavior with later per-slot fallback behavior.

## Testing strategy

Run:

```bash
make lint
```

Optional targeted checks before lint:

```bash
grep -R "Claude-only fallback\|auto-proceed degraded\|BOTH_DOWN=false" -n docs/skills.md docs/external-reviewers.md
```

Expected result:

- No stale "Claude-only fallback" remains in the `/status` catalog entry.
- `docs/external-reviewers.md` no longer says one-down auto-proceeds without a sentinel or both-down prompts.
- `docs/external-reviewers.md` documents the Continue-sentinel proceed-degraded path for one-down runs.

## Acceptance

- `docs/skills.md` `/status` entry no longer says "Claude-only fallback".
- `docs/external-reviewers.md` degraded-tools gate paragraph describes one-down as requiring Continue/Abort (not auto-proceeding), and both-down as hard-failing (not prompting).
- `make lint` passes.

diff_lines: 6

## Test plan
(no test plan section in plan-file)
