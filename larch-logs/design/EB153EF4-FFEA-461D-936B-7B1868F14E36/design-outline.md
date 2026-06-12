## Proposed Design Outline

### Goals
- Absorb the degraded-tools gate and 1.r rebase checkpoint into `python/bootstrap.py`'s continue path on both `--mode initial` and `--mode resume`.
- A non-degraded run reaches Step 2 after one Step 0 Bash call (initial path).
- Fold gate and rebase KVs into the routing envelope so the orchestrator handles `DEGRADED_PROMPT_REQUIRED` and `ROUTE` without extra Bash calls.

### Non-goals
- No changes to 4.r, 7.r, or 7a.r rebase checkpoints.
- No porting of `rebase-checkpoint-probe.sh` shell logic to Python.
- No changes to `/design`'s degraded gate (`design-step0-degraded.sh`).
- No changes to the standalone `python3 cli.py agent degraded-tools-gate` command.

### Approach sketch
- Add `_phase_absorbed_continue()` to `python/bootstrap.py`; it runs unconditionally after `_phase_coder` (initial) and `_phase_plan` (resume), internally gated on the continue conditions (no bail, plan readable, coder available).
- On resume, reads coder from `bootstrap-routing.env` to confirm the continue condition; skips if coder unresolvable.
- Extends `ROUTING_KEYS` with nine new keys; `_emit_final()` emits them.
- Updates SKILL.md to remove explicit gate and 1.r calls; adds `DEGRADED_PROMPT_REQUIRED` to the routing table; retires the degraded gate wrapper call.
- Retires `step-0-degraded-gate.sh/.md`; updates `test-implement-structure.sh`.
- Extends `python/test_bootstrap.py` with absorption tests (non-degraded, one-down, both-down, rebase conflict/bail, sentinel replay on resume).

### Surfaces in scope
- `python/bootstrap.py`
- `python/test_bootstrap.py`
- `skills/implement/SKILL.md`
- `skills/implement/scripts/step-0-degraded-gate.sh` (retire)
- `skills/implement/scripts/step-0-degraded-gate.md` (retire)
- `scripts/test-implement-structure.sh`

### Open questions
- None.
