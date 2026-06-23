## Proposed Design Outline

### Goals
- Emit `CHECKPOINT_NEXT=continue|load-routing` from `python/cli.py push checkpoint-probe` so the orchestrator has a first-class "load the routing file?" directive.
- Collapse four redundant "parse rc + ROUTE, conditionally load file" passages in SKILL.md into a single directive lookup at the Macro section.
- Keep the conflict-resolution file-read prose in one canonical place.

### Non-goals
- Remove or replace `ROUTE=continue|conflict|bail` from the probe output (backward compat).
- Change any conflict resolution logic or step-7a internals.
- Add new routing states beyond `continue` and `load-routing`.

### Approach sketch
- Add `_emit_kv("CHECKPOINT_NEXT", "continue"|"load-routing")` at each exit branch of `_emit_rebase_checkpoint_keys()` in `push.py`.
- In `bootstrap.py`, after ROUTE normalization, set `routing["CHECKPOINT_NEXT"]` derived from the normalized ROUTE; add `CHECKPOINT_NEXT` to `ROUTING_KEYS` so it flows through the Step 0 envelope.
- Update SKILL.md: rewrite the Macro description (line ~158) to gate on `CHECKPOINT_NEXT`; simplify the Step 0 table rows (~293-294) and the three call-site parentheticals (4.r, 7.r, 7a.r).
- Document `CHECKPOINT_NEXT` in `rebase-checkpoint-routing.md`.
- Add `CHECKPOINT_NEXT` assertions to `test_push.py`.

### Surfaces in scope
- `python/push.py` — `_emit_rebase_checkpoint_keys()`
- `python/bootstrap.py` — `ROUTING_KEYS`, probe route normalization block
- `python/test_push.py` — existing checkpoint-probe tests
- `skills/implement/SKILL.md` — Macro section + three call-site parentheticals + Step 0 table
- `skills/implement/references/rebase-checkpoint-routing.md` — document `CHECKPOINT_NEXT`

### Open questions
- None.
