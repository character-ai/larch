# step-5-review.sh

Step 5 review loop launcher. Marks Step 5 telemetry, writes the bg-wait marker, prints the scripted-review banner, reads the persisted difficulty override when present, and runs `review-and-fix step5 --mode loop`.

## Caller

`skills/implement/SKILL.md` invokes this wrapper from the scripted review loop so the prompt-side Bash fence remains one launcher call with immediate-background handling.

## KV grammar

None. The wrapper prints the human-facing Step 5 banner, then relays all stdout and status grammar from `python/cli.py review-and-fix step5` unchanged.

## Invariants

- Bash 3.2 portable; no associative arrays or namerefs.
- Self-rehydrates `CLAUDE_PLUGIN_ROOT` from `$IMPLEMENT_TMPDIR/plugin-root.env` where needed.
- Telemetry marking is best-effort and must not block the review loop.
- `dynamic_archetypes_cap` resolves from `$IMPLEMENT_TMPDIR/session-env.sh`, then from process `LARCH_DYNAMIC_ARCHETYPES_MAX`, then the implement-mode default `1`.
- Writes a `.bg-wait-active` marker (`STEP=implement-step5-review`) before the review call; the EXIT trap writes `.completed/step-5-terminal` and removes the marker on any exit (success or failure). Fail-open: marker/sentinel writes are best-effort and must not abort the review.
- The Python call is not `exec`-replaced so the EXIT trap fires on completion. The shell wrapper and `python/cli.py implement step-5-review` both enforce the same `0..1` dynamic archetype cap and delegate the tier 2/2/3 cap to `review-and-fix step5`.

## Edit-in-sync

Update `skills/implement/SKILL.md`, `scripts/test-implement-structure.sh`, and the Step 5 review harnesses when this contract or argv changes.
